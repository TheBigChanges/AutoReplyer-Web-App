"""Read-only billing: owner isolation, secret allowlist and missing schema."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from psycopg2.errors import UndefinedColumn, UndefinedTable
from server import app as adapter


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.get_user_plan_state.return_value = SimpleNamespace(plan='pro', expires_at=1900000000)
        self.db.get_user_plan.return_value = 'pro'
        self.db.list_user_payments.return_value = [dict(id=7, plan='pro', months=3, stars=95, status='paid', created_at=1800000000, user_id=123, token='secret', charge_id='private', grant_value=95, snap_plan='free')]
        self.pricing = SimpleNamespace(DURATIONS=(1,3,6,12), DURATION_DISCOUNT={1:0,3:10,6:15,12:20}, stars_price=lambda p,m: m*{'plus':15,'pro':35,'ultra':70}[p])
        self.mod = patch.object(adapter, 'modules', return_value=(self.db, Mock(), Mock())); self.mod.start(); self.addCleanup(self.mod.stop)
        self.mods = patch.dict(sys.modules, {'payments':self.pricing}); self.mods.start(); self.addCleanup(self.mods.stop)
        adapter.app.dependency_overrides[adapter.identity] = lambda: {'id':123}
        self.addCleanup(adapter.app.dependency_overrides.clear)
        self.client = TestClient(adapter.app); self.addCleanup(self.client.close)

    def test_owner_history_allowlist_and_current_state(self):
        r = self.client.get('/api/billing?user_id=999&limit=999999')
        self.assertEqual(r.status_code, 200)
        self.db.get_user_plan_state.assert_called_once_with(123)
        self.db.list_user_payments.assert_called_once_with(123, limit=20)
        data = r.json()
        self.assertEqual(data['plan'], 'pro')
        self.assertEqual([c['months'] for c in data['catalog']], [1,3,6,12])
        for key in ['token','charge_id','user_id','grant_value','snap_plan']:
            self.assertNotIn(key, data['history'][0])
        self.assertEqual(r.headers['cache-control'], 'no-store')

    def test_unsigned_and_mutations_are_rejected(self):
        for method in ['post','patch','delete']:
            self.assertEqual(getattr(self.client,method)('/api/billing').status_code,405)
        adapter.app.dependency_overrides.clear()
        self.assertEqual(self.client.get('/api/billing').status_code,401)
        self.db.list_user_payments.assert_not_called()

    def test_missing_schema_is_localized_without_schema_writes(self):
        for exc in [UndefinedTable, UndefinedColumn]:
            self.db.get_user_plan_state.side_effect = exc('private sql')
            for lang,text in [('uz','hali tayyor'),('ru','ещё не готовы'),('en','not ready')]:
                r=self.client.get('/api/billing',headers={'Accept-Language':lang})
                self.assertEqual(r.status_code,503)
                self.assertIn(text,r.json()['detail'])
                self.assertNotIn('private sql',r.text)
        self.db.init_db.assert_not_called()

    def test_admin_effective_access_does_not_replace_purchased_plan(self):
        with patch.dict('os.environ',{'ADMIN_ID':'123'}):
            r=self.client.get('/api/billing').json()
        self.assertEqual((r['plan'],r['effective_plan']),('pro','ultra'))
