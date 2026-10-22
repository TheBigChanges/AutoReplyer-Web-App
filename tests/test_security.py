"""Security boundaries: real signed identity, body limits, plans and owner scope."""
import asyncio
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from server import app as adapter
from server.security import MAX_BODY_BYTES, RequestBodyLimit, valid_origin
from server import security
from test_auth import signed
import test_api


class IdentityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.get_block.return_value = None
        self.env = patch.dict(os.environ, {'BOT_TOKEN': 'test-token', 'ADMIN_ID': '', 'REQUIRED_CHANNEL_ID': ''})
        self.env.start()
        self.modules = patch.object(adapter, 'modules', return_value=(self.db, Mock(), Mock()))
        self.modules.start()
        adapter._requests.clear()
        adapter._membership.clear()
        self.client = TestClient(adapter.app)
        self.headers = {'X-Telegram-Init-Data': signed(auth_date=str(int(time.time())))}

    def tearDown(self):
        self.modules.stop()
        self.env.stop()
        adapter._requests.clear()
        adapter._membership.clear()

    def test_signed_owner_is_used_even_with_identity_in_query(self):
        result = self.client.patch('/api/settings?user_id=999', json={'offline': True}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.db.update_settings.assert_called_once_with(123, offline=True)

    def test_blocked_signed_owner_cannot_write(self):
        self.db.get_block.return_value = {'reason': 'blocked'}
        self.assertEqual(self.client.patch('/api/settings', json={'offline': True}, headers=self.headers).status_code, 403)
        self.db.update_settings.assert_not_called()

    def test_rate_limit_rejects_before_db_write(self):
        adapter._requests[123] = (time.monotonic(), 120)
        self.assertEqual(self.client.patch('/api/settings', json={'offline': True}, headers=self.headers).status_code, 429)
        self.db.update_settings.assert_not_called()

    def test_channel_membership_fails_closed(self):
        with patch.dict(os.environ, {'REQUIRED_CHANNEL_ID': '@channel'}), patch.object(adapter.httpx, 'get') as get:
            get.return_value.json.return_value = {'ok': True, 'result': {'status': 'left'}}
            for _ in range(2):
                self.assertEqual(self.client.patch('/api/settings', json={'offline': True}, headers=self.headers).status_code, 403)
            get.assert_called_once()
            self.db.update_settings.assert_not_called()

    def test_oversized_unsigned_request_rejected_before_identity(self):
        result = self.client.post('/api/faq', content=b' ' * (MAX_BODY_BYTES + 1), headers={'Content-Type': 'application/json', 'Accept-Language': 'en'})
        self.assertEqual(result.status_code, 413)
        self.assertEqual(result.json()['detail'], 'The request body is too large.')
        self.db.get_block.assert_not_called()

    def test_deep_json_is_a_validation_error(self):
        result = self.client.post('/api/faq', content='[' * 10000 + '0' + ']' * 10000, headers={**self.headers, 'Content-Type': 'application/json'})
        self.assertEqual(result.status_code, 422)

    def test_headers_preserve_telegram_embedding_and_disable_api_cache(self):
        result = self.client.get('/api/bootstrap')
        self.assertEqual(result.status_code, 401)
        self.assertEqual(result.headers['cache-control'], 'no-store')
        self.assertEqual(result.headers['x-content-type-options'], 'nosniff')
        self.assertIn('frame-ancestors', result.headers['content-security-policy'])
        self.assertIn('https://web.telegram.org', result.headers['content-security-policy'])
        self.assertIn("object-src 'none'", result.headers['content-security-policy'])
        self.assertNotIn('test-token', result.text)
        for path in ['/', '/app.js', '/config.json']:
            self.assertEqual(self.client.get(path).headers['cache-control'], 'no-cache')
        for path in ['/openapi.json', '/.env', '/server/auth.py', '/../server/auth.py']:
            self.assertEqual(self.client.get(path).status_code, 404)


class PlanAndOwnerTests(unittest.TestCase):
    setUp = test_api.APIIsolationTests.setUp
    tearDown = test_api.APIIsolationTests.tearDown

    def test_paid_settings_cannot_be_written_by_free(self):
        for body in [{'auto_reply_text': 'changed'}, {'sleep_reply_text': 'changed'}, {'ai_role': 'seller'}, {'ai_info': 'changed'}, {'faq_enabled': True}, {'kb_enabled': True}]:
            with self.subTest(body=body):
                self.assertEqual(self.client.patch('/api/settings', json=body).status_code, 403)
        self.db.update_settings.assert_not_called()
        with self.assertRaises(adapter.HTTPException):
            adapter.require(123, 'unknown-feature')

    def test_create_limits_are_passed_to_atomic_upstream_helpers(self):
        for plan, limit in [('plus', 15), ('pro', 30), ('ultra', 65)]:
            self.db.get_user_plan.return_value = plan
            self.db.add_faq_entry.return_value = 5
            self.assertEqual(self.client.post('/api/faq', json={'question': 'Q', 'answer': 'A', 'keywords': ['K']}).status_code, 200)
            self.db.add_faq_entry.assert_called_with(123, question='Q', answer='A', keywords=['K'], max_entries=limit)
        self.db.add_faq_entry.return_value = None
        self.assertEqual(self.client.post('/api/faq', json={'question': 'Q', 'answer': 'A', 'keywords': ['K']}).status_code, 409)

    def test_knowledge_requires_ultra_for_create_edit_and_toggle(self):
        for plan in ['free', 'plus', 'pro']:
            self.db.get_user_plan.return_value = plan
            payload = {'title': 'T', 'content': 'C', 'keywords': ['K']}
            self.assertEqual(self.client.post('/api/knowledge', json=payload).status_code, 403)
            self.assertEqual(self.client.patch('/api/knowledge/9', json=payload).status_code, 403)
            self.assertEqual(self.client.post('/api/knowledge/9/toggle').status_code, 403)
        self.db.add_kb_entry.assert_not_called()
        self.db.update_kb_entry.assert_not_called()
        self.db.toggle_kb_entry.assert_not_called()

    def test_owner_scope_for_all_edit_delete_and_toggle_routes(self):
        self.db.get_user_plan.return_value = 'ultra'
        cases = [('faq', {'question': 'Q', 'answer': 'A', 'keywords': ['K']}, 'faq'), ('knowledge', {'title': 'T', 'content': 'C', 'keywords': ['K']}, 'kb')]
        for kind, body, prefix in cases:
            getattr(self.db, f'update_{prefix}_entry').return_value = False
            self.assertEqual(self.client.patch(f'/api/{kind}/999', json=body).status_code, 404)
            getattr(self.db, f'update_{prefix}_entry').assert_called_with(123, 999, **body)
            getattr(self.db, f'toggle_{prefix}_entry').return_value = None
            self.assertEqual(self.client.post(f'/api/{kind}/999/toggle').status_code, 404)
            getattr(self.db, f'toggle_{prefix}_entry').assert_called_with(123, 999)
        self.db.update_schedule_rule.return_value = ('gone', None)
        self.assertEqual(self.client.patch('/api/schedule/999', json={'days': 1, 'start_min': 1, 'end_min': 2}).status_code, 404)
        self.db.update_schedule_rule.assert_called_with(123, 999, days=1, start_min=1, end_min=2, text=None)
        self.db.get_schedule_rule.return_value = None
        self.assertEqual(self.client.post('/api/schedule/999/toggle').status_code, 404)
        self.db.get_schedule_rule.assert_called_with(123, 999)
        for kind, _, prefix in [*cases, ('schedule', {}, 'schedule')]:
            fn = getattr(self.db, f'delete_{prefix}_entry') if kind != 'schedule' else self.db.delete_schedule_rule
            fn.return_value = False
            self.assertEqual(self.client.delete(f'/api/{kind}/999').status_code, 404)
            fn.assert_called_with(123, 999)

    def test_out_of_range_ids_and_extra_fields_rejected(self):
        for key in ['0', '-1', str(2**40), '1.2']:
            self.assertEqual(self.client.delete(f'/api/faq/{key}').status_code, 422)
        self.db.delete_faq_entry.assert_not_called()
        self.assertEqual(self.client.post('/api/schedule', json={'days': 1, 'start_min': 1, 'end_min': 2, 'owner_user_id': 999}).status_code, 422)
        self.assertEqual(self.client.patch('/api/settings', json={'cooldown_hours': True}).status_code, 422)

    def test_preview_obeys_downgraded_faq_limit(self):
        self.db.get_user_plan.return_value = 'plus'
        self.db.get_settings.return_value = {'faq_enabled': True, 'auto_reply_text': 'Fallback'}
        self.db.get_enabled_faq_entries.return_value = [{'id': n} for n in range(30)]
        self.logic.match_faq = Mock(return_value=None)
        self.assertEqual(self.client.post('/api/test', json={'message': 'Hi'}).status_code, 200)
        self.logic.match_faq.assert_called_once_with('Hi', [{'id': n} for n in range(15)])

    def test_analytics_restricts_payload_not_only_chart_ui(self):
        summary = {'incoming': 20, 'sent': 10, 'kinds': {'ai': 1, 'faq': 2, 'static': 3, 'sleep': 4, 'incoming': 20, 'skipped': 99}, 'hourly': [0]*24, 'hourly_sent': [0]*24, 'peak': None, 'skipped': 99}
        reports = SimpleNamespace(period_start=Mock(return_value=SimpleNamespace(timestamp=lambda: 0)), summarize=Mock(return_value=summary))
        self.db.get_settings.return_value = {'name_clock_tz': 'invalid/timezone'}
        with patch.object(adapter, 'modules', return_value=(self.db, self.logic, reports)):
            for plan in ['free', 'plus', 'pro', 'ultra', 'unknown']:
                self.db.get_user_plan.return_value = plan
                data = self.client.get('/api/analytics?days=1').json()
                self.assertNotIn('skipped', data['kinds'])
                self.assertEqual(data['skipped'], 99 if plan == 'ultra' else None)
                self.assertEqual(set(data['kinds']), {'ai', 'faq', 'static', 'sleep'} if plan in ['pro', 'ultra'] else {'ai'})
                self.assertEqual(data['series'] is None, plan in ['free', 'unknown'])

    def test_schedule_toggle_returns_authoritative_state(self):
        self.db.get_schedule_rule.return_value = {'is_enabled': True}
        self.db.update_schedule_rule.return_value = ('ok', None)
        self.assertIs(self.client.post('/api/schedule/1/toggle').json()['is_enabled'], False)


class StreamLimitTests(unittest.TestCase):
    def test_deployment_origins_reject_wildcards_and_policy_injection(self):
        for origin in ['*', 'null', 'https://*.example', 'https://api.example/path', 'https://api.example;script-src *', 'https://user@api.example', 'https://api.example:99999', 'http://api.example']:
            self.assertFalse(valid_origin(origin), origin)
        self.assertTrue(valid_origin('https://api.example:8443'))
        self.assertTrue(valid_origin('http://127.0.0.1:8768', local_http=True))

    def test_slow_request_body_has_total_deadline(self):
        sent = []
        async def app(scope, receive, send):
            self.fail('Slow body must not reach application')
        async def receive():
            await asyncio.sleep(1)
            return {'type': 'http.request', 'body': b'', 'more_body': True}
        async def send(message):
            sent.append(message)
        with patch.object(security, 'BODY_TIMEOUT_SECONDS', .01):
            asyncio.run(RequestBodyLimit(app)({'type': 'http', 'path': '/api/faq', 'headers': []}, receive, send))
        self.assertEqual(sent[0]['status'], 408)

    def test_stream_without_content_length_is_bounded(self):
        called, sent = [], []
        async def app(scope, receive, send):
            called.append(True)
        parts = iter([{'type': 'http.request', 'body': b'x' * MAX_BODY_BYTES, 'more_body': True}, {'type': 'http.request', 'body': b'x', 'more_body': False}])
        async def receive():
            return next(parts)
        async def send(message):
            sent.append(message)
        asyncio.run(RequestBodyLimit(app)({'type': 'http', 'path': '/api/faq', 'headers': []}, receive, send))
        self.assertEqual(sent[0]['status'], 413)
        self.assertEqual(called, [])
