"""Explicit checkbox intent from stale tabs and localized preview scope."""
import copy
import json
import os
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('AR_BASE_URL','http://127.0.0.1:8765')
STUB='window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    demo=browser.new_context(locale='uz-UZ')
    demo.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB,content_type='application/javascript'))
    seed=demo.new_page()
    seed.goto(BASE)
    seed.locator('[data-setting=offline]').first.locator('xpath=..').click()
    fixture=seed.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['user']={'id':123,'first_name':'Test'}
    fixture['language']='uz'
    context=browser.new_context(locale='uz-UZ',viewport={'width':390,'height':844})
    context.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB.replace('initData:""','initData:"test-session"'),content_type='application/javascript'))
    requests=[]
    errors=[]
    def api(route):
        path=route.request.url.split('/api/')[-1]
        if path=='bootstrap':
            route.fulfill(json=copy.deepcopy(fixture))
        elif path.startswith('analytics'):
            route.fulfill(json={'incoming':0,'sent':0,'kinds':{'ai':0,'faq':0,'static':0,'sleep':0},'peak':None,'skipped':0,'series':None})
        elif path.endswith('/toggle'):
            kind,entry,_=path.split('/')
            body=route.request.post_data_json
            assert set(body)=={'is_enabled'} and isinstance(body['is_enabled'],bool),body
            requests.append((kind,body['is_enabled']))
            group='schedules' if kind=='schedule' else kind
            next(r for r in fixture[group] if r['id']==int(entry))['is_enabled']=body['is_enabled']
            route.fulfill(json={'is_enabled':body['is_enabled']})
        else:
            raise AssertionError('Unexpected API call: '+path)
    context.route('**/api/**',api)
    for kind,route in [('faq','faq'),('knowledge','knowledge'),('schedule','scheduler')]:
        pages=[context.new_page(),context.new_page()]
        for page in pages:
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE+'/#'+route)
            expect(page.locator(f'[data-toggle="{kind}:1"]')).to_be_checked()
        # Both tabs still show the same old checked value, so both intend off.
        for page in pages:
            checkbox=page.locator(f'[data-toggle="{kind}:1"]')
            checkbox.locator('xpath=..').click()
            expect(checkbox).not_to_be_checked()
            expect(checkbox).to_be_enabled()
        assert requests[-2:]==[(kind,False),(kind,False)],requests
        pages[0].reload()
        expect(pages[0].locator(f'[data-toggle="{kind}:1"]')).not_to_be_checked()
        for page in pages:
            page.close()
    preview=context.new_page()
    preview.on('pageerror',lambda error:errors.append(str(error)))
    preview.set_viewport_size({'width':320,'height':800})
    preview.goto(BASE+'/#replies')
    for language,title,words in [
        ('uz','FAQ va oddiy javob sinovi',['AI','uyqu rejimi','jadval']),
        ('ru','Тест FAQ и обычного ответа',['ИИ','режим сна','расписание']),
        ('en','FAQ and standard reply test',['AI','sleep mode','schedules'])]:
        if preview.locator('#header-language').get_attribute('data-current-language')!=language:
            preview.locator('#header-language').click()
            preview.locator(f'#header-language-menu [data-language-option={language}]').click()
        preview.locator('[data-action=test]').click()
        expect(preview.locator('#modal h2')).to_have_text(title)
        note=preview.locator('#modal .hint').inner_text()
        assert all(word in note for word in words),(language,note)
        assert preview.evaluate('document.documentElement.scrollWidth<=innerWidth')
        preview.keyboard.press('Escape')
        expect(preview.locator('#modal')).not_to_be_visible()
    assert not errors,errors
    print(json.dumps({'checks':['three explicit checkbox payloads','same off intent from two stale tabs','three-language preview scope at 320px'],'page_errors':errors}))
    browser.close()
