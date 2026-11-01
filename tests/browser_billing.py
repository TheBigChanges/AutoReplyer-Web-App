"""Billing UI: truthful prices, read-only traffic, retries, races and glass."""
import copy
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get('AR_BASE_URL','http://127.0.0.1:8765')
STUB='window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE','/usr/bin/google-chrome'),headless=True,args=['--no-sandbox'])
    demo=browser.new_context(locale='uz-UZ');demo.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB,content_type='application/javascript'))
    seed=demo.new_page();seed.goto(BASE);seed.locator('[data-setting=offline]').first.locator('xpath=..').click()
    fixture=seed.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))');fixture['user']={'id':123,'first_name':'Billing QA'};fixture['language']='uz'
    ctx=browser.new_context(locale='uz-UZ',viewport={'width':390,'height':844});ctx.route('https://telegram.org/**',lambda r:r.fulfill(body=STUB.replace('initData:""','initData:"signed"'),content_type='application/javascript'))
    data={'plan':'pro','effective_plan':'ultra','expires_at':1900000000,'catalog':[{'months':m,'discount':{1:0,3:10,6:15,12:20}[m],'prices':prices} for m,prices in [(1,{'plus':15,'pro':35,'ultra':70}),(3,{'plus':41,'pro':95,'ultra':189}),(6,{'plus':77,'pro':179,'ultra':357}),(12,{'plus':144,'pro':336,'ultra':672})]],'history':[{'id':1,'plan':'<img src=x onerror=alert(1)>','months':3,'stars':95,'status':'paid','created_at':1800000000}]}
    requests=[];held=[];hold=False;fail=True
    def api(r):
        path=r.request.url.split('/api/')[-1];requests.append((r.request.method,path))
        if path=='bootstrap':r.fulfill(json=copy.deepcopy(fixture))
        elif path.startswith('analytics'):r.fulfill(json={'incoming':0,'sent':0,'kinds':{},'series':None,'skipped':None,'peak':None})
        elif path=='billing':
            if hold:held.append(r)
            elif fail:r.fulfill(status=503,json={'detail':'Billing unavailable'})
            else:r.fulfill(json=copy.deepcopy(data))
        else:raise AssertionError(path)
    ctx.route('**/api/**',api)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(BASE+'/#plans');expect(page.locator('[role=alert]')).to_contain_text('Billing unavailable')
    expect(page.locator('[data-action=billing-history]')).to_be_disabled()
    fail=False;hold=True;page.locator('[data-action=billing-refresh]').click();expect(page.locator('[data-action=billing-refresh]')).to_be_disabled()
    page.evaluate("location.hash='replies'");page.wait_for_timeout(100);assert held
    held.pop().fulfill(json=copy.deepcopy(data));page.wait_for_timeout(150);expect(page.locator('#settings-form[data-kind=replies]')).to_be_visible()
    page.evaluate("location.hash='plans'");expect(page.locator('.price').nth(1)).to_contain_text('15')
    for lang in ['uz','ru','en']:
        page.evaluate('(lang)=>{localStorage.setItem("ar-language",lang)}',lang)
        hold=False;page.reload();expect(page.locator('.price').nth(1)).to_contain_text('15')
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':844})
            for dark in [False,True]:
                page.evaluate('(dark)=>document.body.classList.toggle("dark",dark)',dark)
                page.locator('[data-action=billing-duration][data-months="12"]').click();expect(page.locator('.price').nth(1)).to_contain_text('144')
                page.locator('[data-action=billing-history]').click();expect(page.locator('#modal')).to_be_visible()
                assert not page.locator('#modal img').count()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert 'blur(36px)' in page.locator('#modal').evaluate('(el)=>getComputedStyle(el).backdropFilter')
                page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
                page.locator('[data-action=billing-duration][data-months="1"]').click()
        expect(page.locator('.plans-grid a').first).to_have_attribute('href','https://t.me/autoreplyer_dbot')
    page.set_viewport_size({'width':390,'height':844});page.emulate_media(reduced_motion='reduce');page.locator('[data-action=billing-history]').click();page.wait_for_timeout(100)
    assert page.evaluate('document.getAnimations().length')==0
    Path('artifacts').mkdir(exist_ok=True);page.screenshot(path='artifacts/billing-mobile-dark.png')
    assert all(method=='GET' for method,path in requests),requests
    assert not errors,errors
    print('Billing: catalog 3 languages x 4 widths x 2 themes, retry, held response navigation, XSS, glass, reduced motion, GET-only passed')
    browser.close()
