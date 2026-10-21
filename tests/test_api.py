import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from server import app as adapter


class APIIsolationTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.get_user_plan.return_value = 'free'
        self.db.get_block.return_value = None
        self.logic = SimpleNamespace(SCHEDULE_PLAN_LIMITS={'free': 1, 'ultra': 30}, valid_schedule_time=lambda s, e: (s == 0 and e == 1440) or (s != e and e < 1440))
        self.mod = patch.object(adapter, 'modules', return_value=(self.db, self.logic, Mock()))
        self.mod.start()
        adapter.app.dependency_overrides[adapter.identity] = lambda: {'id': 123, 'first_name': 'Test'}
        self.client = TestClient(adapter.app)

    def tearDown(self):
        adapter.app.dependency_overrides.clear()
        self.mod.stop()

    def test_settings_scoped_to_verified_owner(self):
        result = self.client.patch('/api/settings', json={'offline': True})
        self.assertEqual(result.status_code, 200)
        self.db.update_settings.assert_called_once_with(123, offline=True)

    def test_cannot_set_plan_or_owner_id(self):
        for field in ['owner_user_id', 'plan', 'name_clock_enabled']:
            with self.subTest(field=field):
                result = self.client.patch('/api/settings', json={field: 456})
                self.assertEqual(result.status_code, 422)
        self.db.update_settings.assert_not_called()

    def test_free_cannot_enable_ai_or_create_faq(self):
        self.assertEqual(self.client.patch('/api/settings', json={'ai_enabled': True}).status_code, 403)
        self.assertEqual(self.client.post('/api/faq', json={'question': 'test', 'keywords': ['test'], 'answer': 'test'}).status_code, 403)
        self.db.update_settings.assert_not_called()
        self.db.add_faq_entry.assert_not_called()

    def test_null_settings_and_string_booleans_rejected(self):
        for body in [{'offline': None}, {'offline': 'false'}, {'sleep_start_minutes': 1.5}]:
            self.assertEqual(self.client.patch('/api/settings', json=body).status_code, 422)

    def test_all_day_uses_upstream_format(self):
        self.db.add_schedule_rule.return_value = ('ok', 7)
        response = self.client.post('/api/schedule', json={'days': 127, 'start_min': 0, 'end_min': 1440})
        self.assertEqual(response.status_code, 200)
        self.db.add_schedule_rule.assert_called_once_with(123, days=127, start_min=0, end_min=1440, text=None, max_rules=1)

    def test_schedule_conflict_rejected(self):
        self.db.add_schedule_rule.return_value = ('conflict', 1)
        self.assertEqual(self.client.post('/api/schedule', json={'days': 1, 'start_min': 540, 'end_min': 1080}).status_code, 409)

    def test_other_owners_entry_not_found(self):
        self.db.delete_faq_entry.return_value = False
        self.assertEqual(self.client.delete('/api/faq/999').status_code, 404)
        self.db.delete_faq_entry.assert_called_once_with(123, 999)

    def test_free_analytics_history_denied(self):
        self.assertEqual(self.client.get('/api/analytics?days=30').status_code, 403)
        self.db.get_analytics_rows.assert_not_called()

    def test_unsigned_request_rejected(self):
        adapter.app.dependency_overrides.clear()
        self.assertEqual(self.client.get('/api/bootstrap').status_code, 401)


if __name__ == '__main__':
    unittest.main()
