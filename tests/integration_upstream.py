"""Real pinned upstream + PostgreSQL contract tests, never a production database.

AR_TEST_DATABASE_URL must name a loopback ar_webapp_test* database. Each run owns
one random schema, initializes the bot schema there and drops only that schema.
The production Web App still never calls init_db or runs migrations.
"""
import json
import os
from pathlib import Path
import re
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import psycopg2
from psycopg2 import extensions, sql
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_auth import signed
from scripts.prepare_upstream import verify_source


class UpstreamIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dsn = os.environ.get('AR_TEST_DATABASE_URL', '')
        if not dsn:
            raise RuntimeError('Set AR_TEST_DATABASE_URL to an isolated loopback ar_webapp_test* database.')
        config = extensions.parse_dsn(dsn)
        if config.get('host') not in ('127.0.0.1', 'localhost', '::1') or not config.get('dbname', '').startswith('ar_webapp_test'):
            raise RuntimeError('Only a loopback ar_webapp_test* database is permitted.')
        if config.get('hostaddr') not in (None, '127.0.0.1', '::1'):
            raise RuntimeError('A non-loopback hostaddr is not permitted.')
        # Pin the network address too, overriding a possible PGHOSTADDR env value.
        dsn = extensions.make_dsn(dsn, hostaddr='::1' if config['host'] == '::1' else '127.0.0.1')
        source = Path(os.environ['AUTOREPLYER_SOURCE']).resolve()
        manifest_path = Path(os.environ.get('AR_TEST_UPSTREAM_MANIFEST') or ROOT / 'docs/upstream-integration.json')
        manifest = json.loads(manifest_path.read_text())
        pin = re.search(r'ARG AUTOREPLYER_REF=([0-9a-f]{40})', (ROOT / 'Dockerfile').read_text()).group(1)
        verify_source(source, manifest, pin)
        cls.schema = 'ar_integration_' + uuid4().hex
        cls.admin = psycopg2.connect(dsn)
        cls.admin.autocommit = True
        with cls.admin.cursor() as cur:
            cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(cls.schema)))
        cls.addClassCleanup(cls.cleanup_schema)
        cls.environment = patch.dict(os.environ, {
            'DATABASE_URL': extensions.make_dsn(dsn, options=f'-csearch_path={cls.schema}'),
            'BOT_TOKEN': 'test-token', 'ADMIN_ID': '', 'REQUIRED_CHANNEL_ID': ''})
        cls.environment.start()
        cls.addClassCleanup(cls.environment.stop)
        from server import app as adapter
        cls.adapter = adapter
        cls.db, cls.logic, cls.reports = adapter.modules()
        cls.addClassCleanup(cls.db._get_pool().closeall)
        cls.db.init_db()  # Test-only schema; never called by the adapter.
        cls.client = TestClient(adapter.app)
        cls.addClassCleanup(cls.client.close)
        cls.next_uid = 81000
        assert 'bot' not in sys.modules, 'Importing the adapter must not start the bot.'

    @classmethod
    def cleanup_schema(cls):
        with cls.admin.cursor() as cur:
            cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
        cls.admin.close()

    def setUp(self):
        self.adapter._requests.clear()
        self.uid = self.owner('ultra')

    def owner(self, plan):
        type(self).next_uid += 1
        uid = type(self).next_uid
        self.db.set_user_plan(uid, plan)
        return uid

    def request(self, method, path, uid=None, **kwargs):
        uid = self.uid if uid is None else uid
        headers = {'X-Telegram-Init-Data': signed(auth_date=str(int(time.time())), user=json.dumps({'id': uid, 'first_name': 'Integration'}))}
        return self.client.request(method, path, headers=headers, **kwargs)

    def test_bootstrap_uses_real_connection_settings_language_and_owner(self):
        other = self.owner('ultra')
        self.db.upsert_connection(self.uid, 'test-business', True, True)
        self.db.set_user_lang(self.uid, 'ru')
        self.db.update_settings(self.uid, offline=True, auto_reply_text='Own reply')
        self.db.add_faq_entry(other, 'Private question', ['private'], 'Private answer', 65)
        response = self.request('GET', '/api/bootstrap')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['id'], self.uid)
        self.assertEqual(data['language'], 'ru')
        self.assertEqual(data['plan'], 'ultra')
        self.assertEqual(data['connection'], {'is_enabled': True, 'can_reply': True})
        self.assertEqual(data['settings']['auto_reply_text'], 'Own reply')
        self.assertEqual(data['ai_usage'], 0)
        self.assertEqual(data['faq'], [])

    def test_faq_and_knowledge_crud_state_and_cross_owner_isolation(self):
        other = self.owner('ultra')
        for kind, body, changed, getter in [
            ('faq', {'question':'Q', 'keywords':['hours'], 'answer':'A'}, {'question':'Q2', 'keywords':['new'], 'answer':'A2'}, self.db.get_faq_entry),
            ('knowledge', {'title':'T', 'keywords':['facts'], 'content':'C'}, {'title':'T2', 'keywords':['new'], 'content':'C2'}, self.db.get_kb_entry)]:
            created = self.request('POST', f'/api/{kind}', json=body)
            self.assertEqual(created.status_code, 200)
            entry = created.json()['id']
            self.assertEqual(self.request('PATCH', f'/api/{kind}/{entry}', json=changed).status_code, 200)
            for key, value in changed.items():
                self.assertEqual(getter(self.uid, entry)[key], value)
            for desired in [False, False, True, True]:
                result = self.request('POST', f'/api/{kind}/{entry}/toggle', json={'is_enabled':desired})
                self.assertEqual(result.status_code, 200)
                self.assertIs(result.json()['is_enabled'], desired)
                self.assertIs(getter(self.uid, entry)['is_enabled'], desired)
            self.assertEqual(self.request('PATCH', f'/api/{kind}/{entry}', uid=other, json=changed).status_code, 404)
            self.assertEqual(self.request('POST', f'/api/{kind}/{entry}/toggle', uid=other, json={'is_enabled':False}).status_code, 404)
            self.assertEqual(self.request('DELETE', f'/api/{kind}/{entry}', uid=other).status_code, 404)
            self.assertEqual(self.request('DELETE', f'/api/{kind}/{entry}').status_code, 200)
            self.assertIsNone(getter(self.uid, entry))

    def test_settings_and_feature_plan_matrix_with_expiry(self):
        for plan in ['free', 'plus', 'pro', 'ultra']:
            uid = self.owner(plan)
            for body, allowed in [({'auto_reply_text':'Custom'},plan!='free'), ({'sleep_reply_text':'Sleep'},plan!='free'), ({'faq_enabled':True},plan!='free'), ({'ai_enabled':True},plan=='ultra'), ({'kb_enabled':True},plan=='ultra')]:
                self.assertEqual(self.request('PATCH','/api/settings',uid=uid,json=body).status_code,200 if allowed else 403,(plan,body))
            for kind, body, allowed in [('faq',{'question':'Q','keywords':['test'],'answer':'A'},plan!='free'),('knowledge',{'title':'T','keywords':['test'],'content':'C'},plan=='ultra')]:
                self.assertEqual(self.request('POST',f'/api/{kind}',uid=uid,json=body).status_code,200 if allowed else 403)
            self.assertEqual(self.request('PATCH','/api/settings',uid=uid,json={'plan':'ultra'}).status_code,422)
        expired = self.owner('ultra')
        self.db.set_user_plan(expired,'ultra',time.time()-60)
        self.assertEqual(self.request('GET','/api/bootstrap',uid=expired).json()['plan'],'free')
        self.assertEqual(self.request('PATCH','/api/settings',uid=expired,json={'ai_enabled':True}).status_code,403)

    def test_faq_and_knowledge_limits_are_atomic_at_each_plan_boundary(self):
        for kind, plan, limit in [('faq','plus',15),('faq','pro',30),('faq','ultra',65),('knowledge','ultra',55)]:
            uid = self.owner(plan)
            if kind == 'faq':
                body={'question':'Boundary','keywords':['boundary'],'answer':'A'}
                for i in range(limit-1):
                    self.assertIsNotNone(self.db.add_faq_entry(uid,f'Q{i}',['seed'],'A',limit))
                count=self.db.count_faq_entries
            else:
                body={'title':'Boundary','keywords':['boundary'],'content':'C'}
                for i in range(limit-1):
                    self.assertIsNotNone(self.db.add_kb_entry(uid,f'T{i}','C',['seed'],limit))
                count=self.db.count_kb_entries
            barrier=Barrier(2)
            def create(_):
                barrier.wait(timeout=5)
                return self.request('POST',f'/api/{kind}',uid=uid,json=body).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses=list(pool.map(create,range(2)))
            self.assertEqual(sorted(statuses),[200,409],(kind,plan,statuses))
            self.assertEqual(count(uid),limit)

    def test_scheduler_limits_each_plan_and_concurrent_last_slot(self):
        for plan, limit in [('free',1),('plus',3),('pro',10),('ultra',30)]:
            uid=self.owner(plan)
            for i in range(limit-1):
                self.assertEqual(self.db.add_schedule_rule(uid,1,i*3,i*3+1,None,limit)[0],'ok')
            barrier=Barrier(2)
            def create(i):
                barrier.wait(timeout=5)
                return self.request('POST','/api/schedule',uid=uid,json={'days':1,'start_min':300+i*3,'end_min':301+i*3}).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses=list(pool.map(create,range(2)))
            self.assertEqual(sorted(statuses),[200,409],(plan,statuses))
            self.assertEqual(self.db.count_schedule_rules(uid),limit)

    def test_scheduler_edit_conflict_midnight_cache_and_owner_scope(self):
        body={'days':1,'start_min':1380,'end_min':60,'text':'Overnight'}
        first=self.request('POST','/api/schedule',json=body).json()['id']
        self.assertEqual(self.request('POST','/api/schedule',json={'days':2,'start_min':0,'end_min':30}).status_code,409)
        second=self.request('POST','/api/schedule',json={'days':2,'start_min':120,'end_min':180}).json()['id']
        self.assertEqual(self.request('PATCH',f'/api/schedule/{second}',json={'days':2,'start_min':0,'end_min':30}).status_code,409)
        self.assertEqual(self.request('PATCH',f'/api/schedule/{first}',json={'days':1,'start_min':1320,'end_min':60,'text':'Changed'}).status_code,200)
        self.db.get_schedule_rules_cached(self.uid)
        self.assertEqual(self.request('POST',f'/api/schedule/{first}/toggle',json={'is_enabled':False}).status_code,200)
        self.assertIs(next(r for r in self.db.get_schedule_rules_cached(self.uid) if r['id']==first)['is_enabled'],False)
        other=self.owner('ultra')
        for method,path,payload in [('PATCH',f'/api/schedule/{first}',body),('POST',f'/api/schedule/{first}/toggle',{'is_enabled':True}),('DELETE',f'/api/schedule/{first}',None)]:
            self.assertEqual(self.request(method,path,uid=other,json=payload).status_code,404)
        self.assertEqual(self.request('DELETE',f'/api/schedule/{first}').status_code,200)
        self.assertIsNone(self.db.get_schedule_rule(self.uid,first))

    def test_parallel_schedule_state_requests_and_retries_are_idempotent(self):
        status,entry=self.db.add_schedule_rule(self.uid,1,540,600,None,30)
        self.assertEqual(status,'ok')
        for desired in [False,False,True,True]:
            barrier=Barrier(4)
            def change(_):
                barrier.wait(timeout=5)
                return self.request('POST',f'/api/schedule/{entry}/toggle',json={'is_enabled':desired})
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses=list(pool.map(change,range(4)))
            self.assertEqual([r.status_code for r in responses],[200]*4)
            self.assertTrue(all(r.json()['is_enabled'] is desired for r in responses))
            self.assertIs(self.db.get_schedule_rule(self.uid,entry)['is_enabled'],desired)
        self.assertEqual(self.request('POST',f'/api/schedule/{entry}/toggle').status_code,422)

    def test_automation_real_engine_crud_owner_scope_and_delete_confirmation(self):
        engine = self.adapter.automation_engine()
        body = {'name': 'Prices', 'keyword': 'narx*', 'reply': 'Own original answer 🌿', 'priority': 100}
        created = self.request('POST', '/api/automation', json=body)
        self.assertEqual(created.status_code, 200)
        entry = created.json()['id']
        rules = self.db.list_automation_rules(self.uid)
        self.assertEqual(len(rules), 1)
        self.assertIs(rules[0]['is_enabled'], True)
        self.assertEqual(engine.find_matching_automation('Telefon narxi qancha?', rules)['id'], entry)
        self.assertIsNone(engine.find_matching_automation('Narx emas', rules))
        self.assertIsNone(engine.find_matching_automation('unarxon', rules))
        # Exact words, phrases and deterministic priority use the original bot engine.
        for keyword, message, expected in [('narx','narxi',False), ('ish vaqti','ISH VAQTI qanday?',True), ('O‘zbekiston','Ozbekiston',True)]:
            rule = engine.make_keyword_rule(keyword, 'A')
            self.assertEqual(engine.rule_matches(message, rule), expected)
        second = self.request('POST', '/api/automation', json={**body, 'name':'First priority', 'priority':5}).json()['id']
        self.assertEqual(engine.find_matching_automation('narxi', self.db.get_enabled_automation_rules(self.uid))['id'], second)
        other = self.owner('ultra')
        for desired in [False, False, True, True]:
            result = self.request('POST', f'/api/automation/{entry}/toggle', json={'is_enabled': desired})
            self.assertEqual(result.status_code, 200)
            row = next(r for r in self.db.list_automation_rules(self.uid) if r['id'] == entry)
            self.assertIs(row['is_enabled'], desired)
        self.assertEqual(self.request('POST',f'/api/automation/{entry}/toggle',uid=other,json={'is_enabled':False}).status_code,404)
        self.assertEqual(self.request('POST',f'/api/automation/{entry}/delete-confirmation',uid=other).status_code,404)
        token = self.request('POST', f'/api/automation/{entry}/delete-confirmation').json()['token']
        self.assertEqual(self.request('DELETE',f'/api/automation/{entry}',uid=other,json={'token':token}).status_code,409)
        self.assertEqual(self.request('DELETE',f'/api/automation/{entry}',json={'token':token}).status_code,200)
        self.assertEqual(self.request('DELETE',f'/api/automation/{entry}',json={'token':token}).status_code,409)
        self.assertEqual([r['id'] for r in self.db.list_automation_rules(self.uid)],[second])
        for bad in ['*','na*','na*rx','!!!','bir ikki uch tort besh olti']:
            self.assertEqual(self.request('POST','/api/automation',json={**body,'keyword':bad}).status_code,422)

    def test_automation_smart_overnight_and_plan_gate(self):
        body={'name':'Night','keyword':'night','reply':'Night reply','days':[0],'time_range':{'start':1320,'end':360}}
        for p in ['plus','pro','ultra']:
            uid=self.owner(p)
            r=self.request('POST','/api/automation',uid=uid,json=body)
            self.assertEqual(r.status_code,403 if p=='plus' else 200)
            if p=='plus': continue
            rule=self.db.list_automation_rules(uid)[0]
            engine=self.adapter.automation_engine()
            for when,expected in [((0,1320),True),((1,359),True),((1,360),False),((0,1319),False),((2,60),False)]:
                self.assertEqual(engine.rule_matches('night',rule,when=when),expected)
            self.assertFalse(engine.rule_matches('night',rule,when=(0,1400),allow_smart=False))
            self.assertEqual(self.request('POST','/api/automation',uid=uid,json={**body,'time_range':{'start':0,'end':0}}).status_code,422)


    def test_v12_or_edit_preserves_state_counters_and_plan_boundaries(self):
        engine = self.adapter.automation_engine()
        body = {'name':'OR rule','keywords':['narx*','qancha','price'],'reply':'Original','days':[0], 'time_range':{'start':1320,'end':360}}
        r = self.request('POST','/api/automation',json=body)
        self.assertEqual(r.status_code,200,r.text)
        entry = r.json()['id']
        self.assertTrue(engine.rule_matches('qancha', r.json(), when=(1,60)))
        self.assertFalse(engine.rule_matches('qancha', r.json(), when=(1,360)))
        self.assertFalse(engine.rule_matches('narx emas', r.json(), when=(0,1400)))
        self.db.record_automation_sent(self.uid,entry)
        self.db.set_automation_rule_enabled(self.uid,entry,False)
        edited = self.request('PATCH',f'/api/automation/{entry}',json={'name':'Edited','priority':2})
        self.assertEqual(edited.status_code,200,edited.text)
        row = edited.json()
        self.assertEqual(engine.split_keywords(row),body['keywords'])
        self.assertEqual(row['sent_count'],1)
        self.assertIsNotNone(row['last_sent_at'])
        self.assertFalse(row['is_enabled'])
        self.assertEqual((row['name'],row['priority']),('Edited',2))
        other = self.owner('ultra')
        self.assertEqual(self.request('PATCH',f'/api/automation/{entry}',uid=other,json={'reply':'Intrusion'}).status_code,404)
        for keywords in [['narx','NARX'], ['o‘zbek',"o'zbek"], ['x']*6, ['na*'], ['na*rx']]:
            self.assertEqual(self.request('PATCH',f'/api/automation/{entry}',json={'keywords':keywords}).status_code,422,keywords)
        self.assertEqual(self.db.list_automation_rules(self.uid)[0]['action']['text'],'Original')
        self.db.set_user_plan(self.uid,'plus')
        for changes in [{'keywords':['one','two']},{'days':[1]},{'time_range':{'start':1,'end':2}}]:
            self.assertEqual(self.request('PATCH',f'/api/automation/{entry}',json=changes).status_code,403)
        self.assertEqual(self.request('PATCH',f'/api/automation/{entry}',json={'reply':'Basic edit'}).status_code,200)
        retained = self.db.list_automation_rules(self.uid)[0]
        retained['is_enabled'] = True
        self.assertFalse(engine.rule_matches('qancha',retained,when=(1,60),allow_smart=False))
        # A downgrade can remove filters and replace OR with one keyword.
        changed = self.request('PATCH',f'/api/automation/{entry}',json={'keywords':['narx*'],'days':None,'time_range':None})
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(len(changed.json()['conditions']['items']),1)
        self.assertEqual(changed.json()['sent_count'],1)
        self.assertFalse(changed.json()['is_enabled'])
        self.assertEqual(self.request('POST','/api/automation',json=body).status_code,403)

    def test_v12_parallel_partial_edits_merge_without_resetting_other_fields(self):
        entry = self.request('POST','/api/automation',json={'name':'Before','keyword':'hello','reply':'Before'}).json()['id']
        barrier = Barrier(2)
        def change(values):
            barrier.wait(timeout=10)
            return self.request('PATCH',f'/api/automation/{entry}',json=values).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(change,[{'name':'After name'}, {'reply':'After reply'}]))
        self.assertEqual(codes,[200,200])
        row = self.db.list_automation_rules(self.uid)[0]
        self.assertEqual((row['name'],row['action']['text']),('After name','After reply'))
        self.assertEqual(row['sent_count'],0)
        self.assertTrue(row['is_enabled'])

    def test_v12_counters_deletion_race_and_owner_scoped_statistics(self):
        entry = self.request('POST','/api/automation',json={'name':'Counter','keyword':'counter','reply':'Private answer'}).json()['id']
        other = self.owner('ultra')
        self.assertFalse(self.db.record_automation_sent(other,entry))
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(pool.map(lambda _:self.db.record_automation_sent(self.uid,entry),range(8))))
        self.db.add_automation_deleted_sent(other,999)
        self.db.record_analytics(self.uid,'automation',n=4)
        self.db.record_analytics(self.uid,'automation',n=2,ts=time.time()-10*86400)
        stats = self.request('GET','/api/automation/stats').json()
        self.assertEqual((stats['all_sent'],stats['period_sent']),(8,4))
        self.assertEqual(stats['top'],[{'id':entry,'name':'Counter','sent_count':8}])
        self.assertIsNotNone(stats['counters_since'])
        token = self.request('POST',f'/api/automation/{entry}/delete-confirmation').json()['token']
        barrier = Barrier(2)
        def send():
            barrier.wait(timeout=10)
            if not self.db.record_automation_sent(self.uid,entry):
                self.db.add_automation_deleted_sent(self.uid)
        def delete():
            barrier.wait(timeout=10)
            return self.request('DELETE',f'/api/automation/{entry}',json={'token':token}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            sent = pool.submit(send); deleted = pool.submit(delete)
            sent.result(); self.assertEqual(deleted.result(),200)
        stats = self.request('GET','/api/automation/stats').json()
        self.assertEqual((stats['all_sent'],stats['deleted_sent'],stats['total_rules']),(9,9,0))
        self.assertEqual(stats['top'],[])
        self.assertEqual(self.db.get_automation_deleted_sent(other),999)
        self.assertEqual(self.request('PATCH',f'/api/automation/{entry}',json={'name':'Gone'}).status_code,404)
        self.db.set_user_plan(self.uid,'plus')
        self.assertEqual(self.request('GET','/api/automation/stats').status_code,200)
        self.db.set_user_plan(self.uid,'free')
        self.assertEqual(self.request('GET','/api/automation/stats').status_code,403)

    def test_automation_plan_expiry_and_atomic_last_slot_for_all_paid_plans(self):
        engine = self.adapter.automation_engine()
        body = {'name':'Boundary','keyword':'boundary','reply':'A','priority':100}
        for plan, limit in [('plus',2),('pro',10),('ultra',30)]:
            uid = self.owner(plan)
            clean = engine.make_keyword_rule('seed','A')
            for _ in range(limit-1):
                self.assertIsNotNone(self.db.add_automation_rule(uid,**clean,max_rules=limit,enabled=True))
            barrier = Barrier(2)
            def create(_):
                barrier.wait(timeout=5)
                return self.request('POST','/api/automation',uid=uid,json=body).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = list(pool.map(create,range(2)))
            self.assertEqual(sorted(statuses),[200,409],(plan,statuses))
            self.assertEqual(self.db.count_automation_rules(uid),limit)
            self.assertEqual(len(self.request('GET','/api/bootstrap',uid=uid).json()['automation']),limit)
            self.db.set_user_plan(uid,plan,time.time()-60)
            entry = self.db.list_automation_rules(uid)[0]['id']
            self.assertEqual(self.request('POST','/api/automation',uid=uid,json=body).status_code,403)
            self.assertEqual(self.request('POST',f'/api/automation/{entry}/toggle',uid=uid,json={'is_enabled':False}).status_code,403)
            self.assertEqual(self.request('POST',f'/api/automation/{entry}/delete-confirmation',uid=uid).status_code,403)
            self.assertEqual(self.request('GET','/api/bootstrap',uid=uid).json()['automation'],[])
            self.assertEqual(self.db.count_automation_rules(uid),limit)  # Retained after downgrade.

    def test_analytics_real_counters_periods_and_plan_payload(self):
        other=self.owner('ultra')
        for kind,n in [('incoming',13),('ai',2),('faq',3),('static',1),('sleep',1),('automation',2),('skipped',4)]:
            self.db.record_analytics(self.uid,kind,n=n)
        self.db.record_analytics(self.uid,'incoming',ts=time.time()-2*86400,n=5)
        self.db.record_analytics(other,'incoming',n=999)
        for plan in ['free','plus','pro','ultra']:
            self.db.set_user_plan(self.uid,plan)
            for days,allowed in [(1,True),(7,plan!='free'),(30,plan in ['pro','ultra'])]:
                response=self.request('GET',f'/api/analytics?days={days}')
                self.assertEqual(response.status_code,200 if allowed else 403)
                if not allowed:
                    continue
                data=response.json()
                self.assertEqual(data['incoming'],13 if days==1 else 18)
                self.assertEqual(data['sent'],9)
                self.assertEqual(set(data['kinds']),{'ai','faq','static','sleep','automation'} if plan in ['pro','ultra'] else {'ai'})
                self.assertEqual(data['skipped'],4 if plan=='ultra' else None)
                self.assertNotIn('skipped',data['kinds'])
                if plan=='free':
                    self.assertIsNone(data['series'])
                else:
                    self.assertEqual(sum(data['series']['inc']),data['incoming'])
                    self.assertEqual(sum(data['series']['sent']),9)
                    self.assertEqual(len(data['series']['labels']),24 if days==1 else days)

    def test_preview_is_saved_faq_or_standard_without_ai_or_message_side_effects(self):
        self.db.update_settings(self.uid,faq_enabled=True,ai_enabled=True,sleep_mode_enabled=True,scheduler_enabled=True,auto_reply_text='Saved fallback')
        for i in range(16):
            self.db.add_faq_entry(self.uid,f'Q{i}',['outside-limit' if i==15 else f'keyword-{i}'],'Saved FAQ',65)
        self.db.set_user_plan(self.uid,'plus')
        with patch('httpx.get',side_effect=AssertionError('Preview must not call Telegram')), patch('httpx.post',side_effect=AssertionError('Preview must not call an external service')):
            self.assertEqual(self.request('POST','/api/test',json={'message':'outside-limit'}).json()['text'],'Saved fallback')
            self.assertEqual(self.request('POST','/api/test',json={'message':'keyword-0'}).json(),{'source':'Smart FAQ','text':'Saved FAQ'})
        self.assertEqual(self.db.get_analytics_rows(self.uid,0),[])
        self.assertEqual(self.db.get_ai_usage(self.uid,datetime.now().date().isoformat()),0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
