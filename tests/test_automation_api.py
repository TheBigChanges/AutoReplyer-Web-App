"""Automation auth/plan boundaries and expiring, owner-bound one-use deletes."""
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import test_api
from server import app as adapter

BODY = {'name': 'Prices', 'keyword': 'narx*', 'reply': '<b>Original</b>', 'priority': 100}
CLEAN = {'name': 'Prices', 'conditions': {'operator': 'all', 'items': [{'type': 'keyword_contains', 'value': 'narx*'}]}, 'action': {'type': 'send_reply', 'text': '<b>Original</b>'}, 'priority': 100}


class AutomationAPITests(unittest.TestCase):
    def setUp(self):
        test_api.APIIsolationTests.setUp(self)
        self.addCleanup(test_api.APIIsolationTests.tearDown, self)
        self.env = patch.dict(os.environ, {'ADMIN_ID': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        adapter._automation_confirmations.clear()
        self.addCleanup(adapter._automation_confirmations.clear)
        self.db.get_user_plan.return_value = 'plus'
        self.db.list_automation_rules.return_value = [{'id': 7}]
        self.db.delete_automation_rule.return_value = True
        self.engine = Mock()
        self.engine.AutomationError = ValueError
        self.engine.make_keyword_rule.return_value = CLEAN
        self.importer = patch.object(adapter, 'automation_engine', return_value=self.engine)
        self.importer.start()
        self.addCleanup(self.importer.stop)

    def issue(self, entry=7):
        r = self.client.post(f'/api/automation/{entry}/delete-confirmation')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['expires_in'], 120)
        return r.json()['token']

    def delete(self, token, entry=7):
        return self.client.request('DELETE', f'/api/automation/{entry}', json={'token': token})

    def test_all_paid_plans_validate_and_use_atomic_twenty_rule_limit(self):
        for plan in ['plus', 'pro', 'ultra']:
            self.db.get_user_plan.return_value = plan
            self.db.add_automation_rule.return_value = 7
            r = self.client.post('/api/automation', json=BODY)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), {'id': 7, 'is_enabled': True, **CLEAN})
            self.engine.make_keyword_rule.assert_called_with('narx*', '<b>Original</b>', 'Prices', 100)
            self.db.add_automation_rule.assert_called_with(123, **CLEAN, max_rules=20, enabled=True)
        self.db.add_automation_rule.return_value = None
        self.assertEqual(self.client.post('/api/automation', json=BODY).status_code, 409)

    def test_free_and_unknown_plan_cannot_create_toggle_confirm_or_delete(self):
        token = self.issue()
        for plan in ['free', 'unknown']:
            self.db.get_user_plan.return_value = plan
            self.assertEqual(self.client.post('/api/automation', json=BODY).status_code, 403)
            self.assertEqual(self.client.post('/api/automation/7/toggle', json={'is_enabled': False}).status_code, 403)
            self.assertEqual(self.client.post('/api/automation/7/delete-confirmation').status_code, 403)
            self.assertEqual(self.delete(token).status_code, 403)
        self.db.add_automation_rule.assert_not_called()
        self.db.set_automation_rule_enabled.assert_not_called()
        self.db.delete_automation_rule.assert_not_called()

    def test_unsigned_and_blocked_requests_are_rejected(self):
        adapter.app.dependency_overrides.clear()
        self.assertEqual(self.client.post('/api/automation', json=BODY).status_code, 401)
        with patch.dict(os.environ, {'BOT_TOKEN': 'test-token', 'REQUIRED_CHANNEL_ID': ''}):
            from test_auth import signed
            self.db.get_block.return_value = {'reason': 'blocked'}
            adapter._requests.clear()
            self.assertEqual(self.client.post('/api/automation', json=BODY, headers={'X-Telegram-Init-Data': signed(auth_date=str(int(time.time())))}).status_code, 403)
        self.db.add_automation_rule.assert_not_called()

    def test_overposting_invalid_lengths_and_types_rejected(self):
        for change in [{'owner_user_id': 999}, {'is_enabled': False}, {'conditions': {}}, {'priority': True}, {'priority': '1'}, {'priority': -1}, {'priority': 10001}, {'name': ' '}, {'keyword': 'x'*51}, {'reply': 'x'*501}]:
            self.assertEqual(self.client.post('/api/automation', json={**BODY, **change}).status_code, 422, change)
        self.db.add_automation_rule.assert_not_called()
        self.engine.make_keyword_rule.side_effect = ValueError('invalid keyword')
        r = self.client.post('/api/automation', json=BODY, headers={'Accept-Language': 'en'})
        self.assertEqual(r.status_code, 422)
        self.assertIn('1–50', r.json()['detail'])
        self.assertNotIn('invalid keyword', r.text)

    def test_toggle_is_explicit_idempotent_and_scoped(self):
        for desired in [False, False, True, True]:
            r = self.client.post('/api/automation/7/toggle', json={'is_enabled': desired})
            self.assertEqual(r.json(), {'is_enabled': desired})
            self.db.set_automation_rule_enabled.assert_called_with(123, 7, desired)
        self.db.set_automation_rule_enabled.return_value = False
        self.assertEqual(self.client.post('/api/automation/99/toggle', json={'is_enabled': False}).status_code, 404)
        for body in [{}, {'is_enabled': 'false'}, {'is_enabled': False, 'owner_user_id': 99}]:
            self.assertEqual(self.client.post('/api/automation/7/toggle', json=body).status_code, 422)

    def test_confirmation_is_required_scoped_and_consumed_once(self):
        self.assertEqual(self.client.delete('/api/automation/7').status_code, 422)
        self.assertEqual(self.client.post('/api/automation/99/delete-confirmation').status_code, 404)
        token = self.issue()
        adapter.app.dependency_overrides[adapter.identity] = lambda: {'id': 456}
        self.assertEqual(self.delete(token).status_code, 409)
        adapter.app.dependency_overrides[adapter.identity] = lambda: {'id': 123}
        self.assertEqual(self.delete(token, 8).status_code, 409)
        self.assertEqual(self.delete('x'*43).status_code, 409)
        self.assertEqual(self.delete(token).status_code, 200)
        self.assertEqual(self.delete(token).status_code, 409)
        self.db.delete_automation_rule.assert_called_once_with(123, 7)

    def test_confirmation_expiry_newer_dialog_and_parallel_replay(self):
        first = self.issue()
        token = self.issue()
        self.assertEqual(self.delete(first).status_code, 409)
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(lambda _: self.delete(token).status_code, range(2)))
        self.assertEqual(sorted(codes), [200, 409])
        self.db.delete_automation_rule.assert_called_once()
        token = self.issue()
        entry, token, _ = adapter._automation_confirmations[123]
        adapter._automation_confirmations[123] = (entry, token, time.monotonic()-1)
        self.assertEqual(self.delete(token).status_code, 409)

    def test_missing_bot_migration_keeps_bootstrap_usable_and_writes_fail_closed(self):
        from psycopg2.errors import UndefinedTable
        self.db.get_settings.return_value = {}
        self.db.get_connection.return_value = None
        self.db.get_user_lang.return_value = 'uz'
        for name in ['list_faq_entries', 'list_kb_entries', 'list_schedule_rules']:
            getattr(self.db, name).return_value = []
        self.db.get_ai_usage.return_value = 0
        self.db.list_automation_rules.side_effect = UndefinedTable('table not deployed')
        r = self.client.get('/api/bootstrap')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['automation'], [])
        self.assertIs(r.json()['automation_available'], False)
        self.db.add_automation_rule.side_effect = UndefinedTable('table not deployed')
        r = self.client.post('/api/automation', json=BODY, headers={'Accept-Language':'en'})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['detail'], 'Start the updated bot first. The Automation database is not ready yet.')
        self.assertNotIn('table not deployed', r.text)

    def test_bootstrap_exposes_only_owner_rules_and_hides_them_on_free(self):
        self.db.get_settings.return_value = {}
        self.db.get_connection.return_value = None
        self.db.get_user_lang.return_value = 'uz'
        for name in ['list_faq_entries', 'list_kb_entries', 'list_schedule_rules']:
            getattr(self.db, name).return_value = []
        self.db.get_ai_usage.return_value = 0
        self.assertEqual(self.client.get('/api/bootstrap').json()['automation'], [{'id': 7}])
        self.db.list_automation_rules.assert_called_with(123)
        self.db.list_automation_rules.reset_mock()
        self.db.get_user_plan.return_value = 'free'
        self.assertEqual(self.client.get('/api/bootstrap').json()['automation'], [])
        self.db.list_automation_rules.assert_not_called()


if __name__ == '__main__':
    unittest.main()
