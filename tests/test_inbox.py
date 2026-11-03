"""Smart Inbox API: strict writes, privacy, tariff gates, explicit states."""
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from psycopg2.errors import UndefinedTable, UndefinedColumn
from server import app as adapter

class InboxTests(unittest.TestCase):
    def setUp(self):
        self.db=Mock();self.db.get_user_plan.return_value='pro';self.db.get_settings.return_value={'name_clock_tz':'America/New_York'}
        self.db.get_inbox_settings.return_value={'enabled':True,'notify':True,'digest_minutes':600,'digest_claim_token':'secret'}
        self.db.get_pending_chats.return_value=(9,[{'chat_id':72,'customer_name':'<script>private</script>','pending_count':3,'waiting_since':1000,'is_priority':True,'owner_user_id':999,'message':'secret'}])
        self.db.get_pending_stats.return_value={'oldest_waiting_since':1000,'priority':1}
        self.db.list_inbox_reminders.return_value=[{'chat_id':72,'customer_name':'Private','due_at':2000,'attempt_token':'secret'}]
        self.db.count_inbox_reminders_for_date.return_value=2
        self.db.set_inbox_priority.return_value='ok';self.db.schedule_inbox_reminder.return_value=10;self.db.cancel_inbox_reminder.return_value=True
        self.engine=SimpleNamespace(INBOX_PLAN_LIMITS={'free':3,'plus':20,'pro':20,'ultra':20},INBOX_PRIORITY_LIMITS={'free':0,'plus':0,'pro':5,'ultra':20},INBOX_REMINDER_DAILY_LIMITS={'free':0,'plus':0,'pro':3,'ultra':10},effective_minutes=lambda v,paid:v if paid else 1200,reminder_due=lambda choice,now,zone:(now+3600,datetime.fromtimestamp(now+3600,zone).date().isoformat()))
        mod=patch.object(adapter,'modules',return_value=(self.db,Mock(),Mock()));mod.start();self.addCleanup(mod.stop)
        modules=patch.dict(sys.modules,{'inbox':self.engine});modules.start();self.addCleanup(modules.stop)
        adapter.app.dependency_overrides[adapter.identity]=lambda:{'id':123};self.addCleanup(adapter.app.dependency_overrides.clear)
        self.client=TestClient(adapter.app);self.addCleanup(self.client.close)

    def test_owner_scope_privacy_and_limit_ignores_query(self):
        r=self.client.get('/api/inbox?owner=999&limit=999');self.assertEqual(r.status_code,200);d=r.json()
        self.db.get_inbox_settings.assert_called_once_with(123)
        args=self.db.get_pending_chats.call_args;self.assertEqual(args.args[:2],(123,20));self.assertTrue(args.kwargs['priority_first'])
        self.assertEqual(d['timezone'],'America/New_York')
        self.assertNotIn('digest_claim_token',r.text);self.assertNotIn('message',d['chats'][0]);self.assertNotIn('owner_user_id',r.text);self.assertNotIn('attempt_token',r.text)
        self.assertEqual(r.headers['cache-control'],'no-store')

    def test_free_defaults_and_server_gates(self):
        self.db.get_user_plan.return_value='free'
        d=self.client.get('/api/inbox').json();self.assertEqual((d['timezone'],d['digest_minutes'],d['limits']['chats']),('Asia/Tashkent',1200,3))
        for path,body in [('/api/inbox/settings',{'digest_minutes':600}),('/api/inbox/chats/72/priority',{'is_priority':True}),('/api/inbox/chats/72/reminder',{'choice':'1h'})]:
            method=self.client.patch if path.endswith('settings') else self.client.post
            self.assertEqual(method(path,json=body).status_code,403)
        self.db.schedule_inbox_reminder.assert_not_called();self.db.set_inbox_priority.assert_not_called()
        self.assertEqual(self.client.post('/api/inbox/chats/72/priority',json={'is_priority':False}).status_code,200)
        self.assertEqual(self.client.delete('/api/inbox/chats/72/reminder').status_code,200)

    def test_strict_inputs_and_disable_confirmation(self):
        for body in [{},{'notify':None},{'enabled':'false'},{'enabled':False},{'digest_minutes':True},{'digest_minutes':500},{'digest_minutes':'600'},{'notify':True,'owner_id':999}]:
            self.assertEqual(self.client.patch('/api/inbox/settings',json=body).status_code,422,body)
        self.db.set_inbox_settings.assert_not_called()
        self.assertEqual(self.client.patch('/api/inbox/settings',json={'enabled':False,'confirm_clear':True}).status_code,200)
        self.db.set_inbox_settings.assert_called_once_with(123,enabled=False)
        for body in [{'choice':'bad'},{'choice':'1h','due_at':1},{'choice':'1h','daily_limit':999}]:
            self.assertEqual(self.client.post('/api/inbox/chats/72/reminder',json=body).status_code,422)
        for cid in ['0','-1','4503599627370496']:
            self.assertEqual(self.client.post(f'/api/inbox/chats/{cid}/priority',json={'is_priority':False}).status_code,422)
        self.assertEqual(self.client.post('/api/inbox/chats/72/priority',json={'is_priority':'false'}).status_code,422)

    def test_explicit_priority_and_db_error_mapping(self):
        for result,code in [('ok',200),('no_chat',404),('disabled',409),('limit',409),('busy',409)]:
            self.db.set_inbox_priority.return_value=result
            r=self.client.post('/api/inbox/chats/72/priority',json={'is_priority':True});self.assertEqual(r.status_code,code)
        self.db.set_inbox_priority.assert_called_with(123,72,True,5)
        self.db.schedule_inbox_reminder.return_value='busy'
        self.assertEqual(self.client.post('/api/inbox/chats/72/reminder',json={'choice':'1h'}).status_code,409)
        self.db.cancel_inbox_reminder.return_value=False
        self.assertEqual(self.client.delete('/api/inbox/chats/72/reminder').status_code,409)

    def test_missing_schema_and_unsigned_requests(self):
        for exc in [UndefinedTable,UndefinedColumn]:
            self.db.get_inbox_settings.side_effect=exc('private sql')
            for lang,part in [('uz','hali tayyor'),('ru','ещё не готова'),('en','not ready')]:
                r=self.client.get('/api/inbox',headers={'Accept-Language':lang});self.assertEqual(r.status_code,503);self.assertIn(part,r.text);self.assertNotIn('private sql',r.text)
        adapter.app.dependency_overrides.clear()
        self.assertEqual(self.client.get('/api/inbox').status_code,401)
        self.assertEqual(self.client.patch('/api/inbox/settings',json={'enabled':True}).status_code,401)

    def test_reminder_due_and_limit_are_server_derived(self):
        r=self.client.post('/api/inbox/chats/72/reminder',json={'choice':'next9'});self.assertEqual(r.status_code,200)
        args=self.db.schedule_inbox_reminder.call_args.args
        self.assertEqual(args[:2],(123,72));self.assertEqual(args[-1],3);self.assertGreater(args[2],10000)
        with patch.dict('os.environ',{'ADMIN_ID':'123'}):
            d=self.client.get('/api/inbox').json();self.assertEqual(d['limits']['reminders'],10)
