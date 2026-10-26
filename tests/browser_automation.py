"""Automation UI: review, localization, safe rendering, held requests and glass."""
import copy
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
ARTIFACTS = Path('artifacts'); ARTIFACTS.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE', '/usr/bin/google-chrome'), headless=True, args=['--no-sandbox'])
    demo = browser.new_context(locale='uz-UZ')
    demo.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB, content_type='application/javascript'))
    seed = demo.new_page(); seed.goto(BASE)
    seed.locator('[data-setting=offline]').first.locator('xpath=..').click()
    fixture = seed.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['user'] = {'id': 123, 'first_name': 'Automation QA'}
    fixture['language'] = 'uz'; fixture['plan'] = 'plus'
    fixture['automation'][0]['name'] = '<img src=x onerror=alert(1)>'
    context = browser.new_context(locale='uz-UZ', viewport={'width': 390, 'height': 844})
    context.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB.replace('initData:""', 'initData:"signed-test"'), content_type='application/javascript'))
    writes = []; held = {}; hold = {'create': False, 'toggle': False, 'confirmation': False}; fail = {'toggle': False}; errors = []
    def api(route):
        path = route.request.url.split('/api/')[-1]
        method = route.request.method
        if path == 'bootstrap': route.fulfill(json=copy.deepcopy(fixture))
        elif path.startswith('analytics'): route.fulfill(json={'incoming': 0, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': None, 'series': None})
        elif path == 'automation':
            body = route.request.post_data_json; writes.append((path, body))
            assert set(body) == {'name', 'keyword', 'reply', 'priority'}
            rule = {'id': 99, 'name': body['name'], 'conditions': {'operator': 'all', 'items': [{'type': 'keyword_contains', 'value': body['keyword']}]}, 'action': {'type': 'send_reply', 'text': body['reply']}, 'priority': body['priority'], 'is_enabled': True}
            fixture['automation'].append(rule)
            if hold['create']: held['create'] = (route, rule)
            else: route.fulfill(json=rule)
        elif path.endswith('/toggle'):
            body = route.request.post_data_json; writes.append((path, body))
            assert set(body) == {'is_enabled'} and isinstance(body['is_enabled'], bool)
            if hold['toggle']: held['toggle'] = (route, body)
            elif fail['toggle']: route.fulfill(status=500, json={'detail': 'Retry test'})
            else:
                next(r for r in fixture['automation'] if r['id'] == int(path.split('/')[1]))['is_enabled'] = body['is_enabled']
                route.fulfill(json=body)
        elif path.endswith('/delete-confirmation'):
            if hold['confirmation']: held['confirmation'] = route
            else: route.fulfill(json={'token': 't'*43, 'expires_in': 120})
        elif method == 'DELETE':
            body = route.request.post_data_json; writes.append((path, body))
            assert body == {'token': 't'*43}, body
            fixture['automation'] = [r for r in fixture['automation'] if r['id'] != int(path.split('/')[1])]
            route.fulfill(json={'ok': True})
        else: raise AssertionError('Unexpected API: '+path)
    context.route('**/api/**', api)
    page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE+'/#automation')
    expect(page.locator('#main h1')).to_have_text('Avtomatlashtirish')
    expect(page.locator('.automation-rule h3')).to_have_text('<img src=x onerror=alert(1)>')
    assert page.locator('.automation-rule img').count() == 0
    expect(page.locator('#no-results')).not_to_be_visible()
    page.locator('#entry-search').fill('zzzz unmatched')
    expect(page.locator('.automation-rule')).not_to_be_visible()
    expect(page.locator('#no-results')).to_be_visible()
    page.locator('#entry-search').fill('')
    expect(page.locator('.automation-rule')).to_be_visible()
    expect(page.locator('#no-results')).not_to_be_visible()
    # Mobile access remains in Settings, and the original five dock routes stay stable.
    assert page.locator('#mobile-nav a').evaluate_all('(els)=>els.map(el=>el.hash)') == ['#dashboard','#replies','#scheduler','#analytics','#settings']
    page.locator('#mobile-nav a[href="#settings"]').click()
    page.locator('.mobile-sections a[href="#automation"]').click()
    expect(page.locator('#main h1')).to_have_text('Avtomatlashtirish')
    for lang, title in [('uz', 'Avtomatlashtirish'), ('ru', 'Автоматизация'), ('en', 'Automation')]:
        if page.locator('#header-language').get_attribute('data-current-language') != lang:
            page.locator('#header-language').click(); page.locator(f'#header-language-menu [data-language-option={lang}]').click()
        expect(page.locator('#main h1')).to_have_text(title)
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width': width, 'height': 920})
            page.wait_for_timeout(480)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (lang, width)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('[data-action=add-automation]').first.click()
        expect(page.locator('#automation-form input[name=name]')).to_be_visible()
        expect(page.locator('[data-action=automation-back]')).not_to_be_visible()
        page.locator('input[name=name]').fill('<script>custom text</script>')
        page.locator('input[name=keyword]').fill('na*rx')
        page.locator('textarea[name=reply]').fill('Original reply 🌿')
        page.locator('#automation-form [type=submit]').click()
        expect(page.locator('#form-error')).not_to_be_empty()
        page.locator('input[name=keyword]').fill('narx*')
        page.locator('#automation-form [type=submit]').click()
        expect(page.locator('#automation-review')).to_be_visible()
        expect(page.locator('#form-error')).to_be_empty()
        expect(page.locator('#automation-review-name')).to_have_text('<script>custom text</script>')
        assert not page.locator('#automation-review script').count()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        blur = page.locator('#automation-review').evaluate('(el)=>getComputedStyle(el).backdropFilter')
        assert 'blur(14px)' in blur, blur
        page.locator('[data-action=automation-back]').click()
        expect(page.locator('textarea[name=reply]')).to_have_value('Original reply 🌿')
        page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    assert not writes, writes
    # Create requires the second explicit confirmation. Duplicate submits are blocked.
    page.locator('[data-action=add-automation]').first.click()
    page.locator('input[name=name]').fill('Delivery')
    page.locator('input[name=keyword]').fill('delivery')
    page.locator('textarea[name=reply]').fill('Your original reply')
    page.locator('#automation-form [type=submit]').click()
    assert not writes
    hold['create'] = True
    page.locator('#automation-form [type=submit]').click()
    page.wait_for_timeout(100)
    expect(page.locator('#automation-form [type=submit]')).to_be_disabled()
    page.locator('#automation-form').evaluate('(el)=>el.requestSubmit()')
    assert len(writes) == 1
    page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    page.locator('[data-action=add-automation]').first.click()
    expect(page.locator('#modal')).not_to_be_visible()
    r, rule = held.pop('create'); r.fulfill(json=rule)
    expect(page.locator('.automation-rule')).to_have_count(2)
    # Pending toggle survives a language change and routes; failure restores saved value.
    page.locator('#entry-search').fill('Delivery')
    hold['toggle'] = True
    checkbox = page.locator('[data-toggle="automation:99"]')
    checkbox.locator('xpath=..').click(); page.wait_for_timeout(80)
    expect(checkbox).to_be_disabled()
    page.locator('#mobile-nav a[href="#settings"]').click()
    page.locator('.mobile-sections a[href="#automation"]').click()
    expect(page.locator('[data-toggle="automation:99"]')).to_be_disabled()
    r, body = held.pop('toggle'); r.fulfill(json=body)
    expect(page.locator('[data-toggle="automation:99"]')).not_to_be_checked()
    expect(page.locator('[data-toggle="automation:99"]')).to_be_enabled()
    page.locator('#entry-search').fill('Delivery')
    hold['toggle'] = False; fail['toggle'] = True
    page.locator('[data-toggle="automation:99"]').locator('xpath=..').click()
    expect(page.locator('[data-toggle="automation:99"]')).to_be_enabled()
    expect(page.locator('[data-toggle="automation:99"]')).not_to_be_checked()
    fail['toggle'] = False
    expect(page.locator('#entry-search')).to_have_value('Delivery')
    page.locator('#entry-search').fill('')
    # Confirmation is cancelled by closing, and stale async responses cannot reopen it.
    page.locator('[data-action="delete-automation:99"]').click()
    expect(page.locator('[data-action="confirm-delete:automation:99"]')).to_be_visible()
    page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    assert not any(path == 'automation/99' for path, _ in writes)
    hold['confirmation'] = True
    page.locator('[data-action="delete-automation:99"]').click(); page.wait_for_timeout(80)
    page.locator('#mobile-nav a[href="#settings"]').click()
    held.pop('confirmation').fulfill(json={'token':'t'*43,'expires_in':120})
    expect(page.locator('#modal')).not_to_be_visible()
    hold['confirmation'] = False
    page.locator('.mobile-sections a[href="#automation"]').click()
    page.locator('[data-action="delete-automation:99"]').click()
    page.locator('[data-action="confirm-delete:automation:99"]').click()
    expect(page.locator('#modal')).not_to_be_visible()
    expect(page.locator('.automation-rule')).to_have_count(1)
    # Screenshots and accessibility preferences use the same premium surfaces.
    page.locator('.automation-rule h3').evaluate('(el)=>el.lastChild.textContent="Narxlar haqida"')
    page.wait_for_timeout(450)
    for dark in [False, True]:
        page.evaluate('(dark)=>document.documentElement.classList.toggle("dark",dark)', dark)
        page.screenshot(path=str(ARTIFACTS/f'automation-mobile-{"dark" if dark else "light"}.png'), full_page=True)
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function('matchMedia("(prefers-reduced-motion: reduce)").matches')
    page.wait_for_timeout(100)
    page.locator('[data-action=add-automation]').first.click()
    assert page.locator('#modal').evaluate('(el)=>el.getAnimations({subtree:true}).filter(a=>a.playState==="running").length') == 0, page.locator('#modal').evaluate('(el)=>el.getAnimations({subtree:true}).map(a=>({type:a.constructor.name,name:a.animationName,target:a.effect.target.outerHTML.slice(0,180),state:a.playState,timing:a.effect.getTiming()}))')
    page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    fixture['automation_available'] = False; page.reload()
    expect(page.locator('#main')).to_contain_text('Waiting for the bot update')
    expect(page.locator('[data-action=add-automation]')).to_have_count(0)
    fixture['automation_available'] = True
    fixture['plan'] = 'free'; page.reload()
    expect(page.locator('[data-action=add-automation]')).to_have_count(0)
    expect(page.locator('[data-toggle^="automation:"]')).to_have_count(0)
    expect(page.locator('#main a[href="#plans"]').first).to_be_visible()
    assert not errors, errors
    print(json.dumps({'checks':['3 locales x 4 widths','escaped user text','review before enabled save','duplicate create prevention','pending toggle and failure recovery','owner token delete payload','stale confirmation navigation','Free lock','glass and reduced motion'], 'page_errors':errors}))
    browser.close()
