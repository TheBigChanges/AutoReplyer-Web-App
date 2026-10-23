"""Desired entry state is mandatory, strictly typed and scoped to the owner."""
import os
import runpy
import unittest
from unittest.mock import patch
import test_api


class EntryStateTests(unittest.TestCase):
    setUp = test_api.APIIsolationTests.setUp
    tearDown = test_api.APIIsolationTests.tearDown

    def test_boolean_state_required_without_implicit_toggle(self):
        self.db.get_user_plan.return_value = 'ultra'
        for kind in ['faq', 'knowledge', 'schedule']:
            for payload in [None, {}, {'is_enabled': None}, {'is_enabled': 'false'}, {'is_enabled': 0}, {'is_enabled': True, 'owner_user_id': 999}]:
                with self.subTest(kind=kind, payload=payload):
                    self.assertEqual(self.client.post(f'/api/{kind}/1/toggle', json=payload).status_code, 422)
        self.db.update_schedule_rule.assert_not_called()
        self.db.set_faq_entry_enabled.assert_not_called()
        self.db.set_kb_entry_enabled.assert_not_called()

    def test_duplicate_faq_and_knowledge_state_does_not_invert(self):
        self.db.get_user_plan.return_value = 'ultra'
        for kind, prefix in [('faq', 'faq'), ('knowledge', 'kb')]:
            setter = getattr(self.db, f'set_{prefix}_entry_enabled')
            setter.return_value = True
            for value in [False, False, True, True]:
                response = self.client.post(f'/api/{kind}/7/toggle', json={'is_enabled': value})
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.json()['is_enabled'], value)
                setter.assert_called_with(123, 7, value)
            getattr(self.db, f'toggle_{prefix}_entry').assert_not_called()

    def test_runner_keeps_one_worker_even_with_platform_worker_environment(self):
        with patch.dict(os.environ, {'WEB_CONCURRENCY': '4'}), patch('uvicorn.run') as run:
            runpy.run_module('server.run', run_name='__main__')
        self.assertEqual(run.call_args.kwargs['workers'], 1)


if __name__ == '__main__':
    unittest.main()
