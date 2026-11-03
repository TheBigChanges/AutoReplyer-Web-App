"""Inbox: consent, owner UI, explicit writes, races, 3 locales, glass and motion."""
import copy
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
Path('artifacts').mkdir(exist_ok=True)
BASE=os.environ.get('AR_BASE_URL','http://127.0.0.1:8765')
STUB='window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE','/usr/bin/google-chrome'),headless=True,args=['--no-sandbox'])
    demo=browser.new_context(locale='uz-UZ');demo.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB,content_type='application/javascript'))
    seed=demo.new_page();seed.goto(BASE);seed.locator('[data-setting=offline]').first.locator('xpath=..').click();fixture=seed.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['user']={'id':123,'first_name':'Inbox QA'};fixture['language']='uz';fixture['plan']='pro'
    ctx=browser.new_context(locale='uz-UZ',viewport={'width':390,'height':844});ctx.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB.replace('initData:""','initData:"signed"'),content_type='application/javascript'))
    data={'settings':{'enabled':True,'notify':True,'digest_minutes':1200},'digest_minutes':1200,'timezone':'Asia/Tashkent','total':1,'oldest_waiting_since':1800000000,'priority_count':0,'limits':{'chats':20,'priority':5,'reminders':3,'time':True},'reminders_today':0,'chats':[{'chat_id':72,'customer_name':'<img src=x onerror=alert(1)>','pending_count':2,'waiting_since':1800000000,'is_priority':False}],'reminders':[]}
    writes=[];held=[];hold=False;fail=False;hold_read=False
    def api(r):
        path=r.request.url.split('/api/')[-1];method=r.request.method
        if path=='bootstrap':r.fulfill(json=copy.deepcopy(fixture));return
        if path.startswith('analytics'):r.fulfill(json={'incoming':0,'sent':0,'kinds':{},'series':None,'skipped':None,'peak':None});return
        if path=='inbox':
            if hold_read:held.append(r)
            elif fail:r.fulfill(status=503,json={'detail':'Inbox unavailable'})
            else:r.fulfill(json=copy.deepcopy(data))
            return
        body=r.request.post_data_json if method!='DELETE' else None;writes.append((method,path,body))
        if hold:held.append(r);return
        if path=='inbox/settings':
            data['settings'].update(body)
            if 'digest_minutes' in body:data['digest_minutes']=body['digest_minutes']
            if body.get('enabled') is False:
                assert body.get('confirm_clear') is True
                data['chats']=[];data['reminders']=[];data['total']=0
        elif path.endswith('/priority'):data['chats'][0]['is_priority']=body['is_priority']
        elif path.endswith('/reminder'):
            data['reminders']=[] if method=='DELETE' else [{'chat_id':72,'customer_name':'Reminder','due_at':1900000000}]
            if method!='DELETE':assert body=={'choice':'next9'}
        else:raise AssertionError(path)
        r.fulfill(json={'ok':True})
    ctx.route('**/api/**',api);page=ctx.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    fail=True;page.goto(BASE+'/#inbox');expect(page.locator('[role=alert]')).to_contain_text('Inbox unavailable')
    fail=False;page.locator('[data-action=inbox-refresh]').click();expect(page.locator('.inbox-chat')).to_have_count(1)
    assert not page.locator('.inbox-list img').count()
    page.locator('[data-action=inbox-priority]').click();expect(page.locator('[data-action=inbox-priority]')).to_have_attribute('aria-pressed','true')
    assert writes[-1][2]=={'is_priority':True}
    page.locator('#inbox-time').select_option('600');expect(page.locator('#inbox-time')).to_have_value('600')
    page.locator('[data-action=inbox-remind]').click();page.locator('[data-choice=next9]').click();expect(page.locator('.inbox-reminder')).to_have_count(1)
    page.locator('[data-action=inbox-cancel]').click();expect(page.locator('.inbox-reminder')).to_have_count(0)
    before=len(writes);page.locator('[data-action=inbox-disable]').click();expect(page.locator('#modal')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible();assert len(writes)==before
    # Held writes disable all inbox controls, survive localization and do not navigate on reply.
    hold=True;page.locator('[data-action=inbox-notify]').click();expect(page.locator('[data-action=inbox-enable], [data-action=inbox-disable]')).to_be_disabled()
    page.locator('#header-language').click();page.locator('[data-language-owner=header-language][data-language-option=en]').click()
    expect(page.locator('[data-action=inbox-disable]')).to_be_disabled()
    page.evaluate("location.hash='replies'");page.wait_for_timeout(100);held.pop().fulfill(json={'ok':True});hold=False
    page.wait_for_timeout(200);expect(page.locator('#settings-form[data-kind=replies]')).to_be_visible()
    page.evaluate("location.hash='inbox'");expect(page.locator('.inbox-chat')).to_have_count(1)
    for lang in ['uz','ru','en']:
        page.evaluate('(lang)=>localStorage.setItem("ar-language",lang)',lang);page.reload();expect(page.locator('.inbox-chat')).to_have_count(1)
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':844})
            for dark in [False,True]:
                page.evaluate('(dark)=>document.documentElement.classList.toggle("dark",dark)',dark)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.locator('[data-action=inbox-remind]').click();expect(page.locator('#modal')).to_be_visible()
                assert 'blur(36px)' in page.locator('#modal').evaluate('(el)=>getComputedStyle(el).backdropFilter')
                assert page.locator('#modal').bounding_box()['width']<=width
                page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
    page.set_viewport_size({'width':390,'height':844})
    page.evaluate('document.documentElement.style.fontSize="24px"')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('document.documentElement.style.fontSize=""')
    page.screenshot(path='artifacts/inbox-mobile-dark.png',full_page=True)
    page.evaluate('document.documentElement.classList.remove("dark")');page.wait_for_timeout(400)
    page.screenshot(path='artifacts/inbox-mobile-light.png',full_page=True)
    page.evaluate('document.documentElement.classList.add("dark")')
    page.emulate_media(reduced_motion='reduce')
    page.locator('[data-action=inbox-disable]').click();page.wait_for_timeout(100);assert page.evaluate('document.getAnimations().length')==0
    Path('artifacts').mkdir(exist_ok=True);page.screenshot(path='artifacts/inbox-disable-dark.png')
    page.locator('[data-action=inbox-confirm-disable]').click();expect(page.locator('[data-action=inbox-enable]')).to_be_visible();expect(page.locator('.inbox-chat')).to_have_count(0)
    assert writes[-1][2]=={'enabled':False,'confirm_clear':True}
    page.locator('[data-action=inbox-enable]').click();expect(page.locator('[data-action=inbox-disable]')).to_be_visible()
    # Free plan controls are visibly locked; enabled and notify remain available.
    fixture['plan']='free';data['limits']={'chats':3,'priority':0,'reminders':0,'time':False};data['chats']=[{'chat_id':72,'customer_name':'Free chat','pending_count':1,'waiting_since':1800000000,'is_priority':False}]
    page.reload();expect(page.locator('#inbox-time')).to_be_disabled();expect(page.locator('[data-action=inbox-priority]')).to_be_disabled();expect(page.locator('[data-action=inbox-remind]')).to_be_disabled()
    assert not errors,errors
    print('Inbox passed: strict explicit writes, destructive consent, pending controls across language/route, XSS, schema retry, Free locks, 3 locales x4 widths x2 themes, glass/reduced motion')
    browser.close()
