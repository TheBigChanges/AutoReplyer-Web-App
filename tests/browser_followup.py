"""Regressions reproduced after the first audit: pending controls and storage."""
import json
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    errors = []
    def context(live=False):
        ctx = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
        stub = STUB.replace('initData:""', 'initData:"fake-session"') if live else STUB
        ctx.route('https://telegram.org/**', lambda r: r.fulfill(body=stub, content_type='application/javascript'))
        return ctx
    def new_page(ctx):
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        return page
    def language(page, lang):
        page.locator('#header-language').click()
        page.locator('#header-language-menu [data-language-option='+lang+']').click()
        expect(page.locator('#header-language')).to_have_attribute('data-current-language', lang)
    def navigate(page, route, field):
        page.evaluate('(r)=>location.hash=r', route)
        expect(page.locator(field)).to_be_visible()

    demo = new_page(context())
    demo.goto(BASE + '/#replies')
    demo.locator('[data-setting=offline]').locator('xpath=..').click()
    expect(demo.locator('#toast')).to_be_visible()
    fixture = demo.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['user'] = {'id': 123, 'first_name': 'Test'}
    fixture['language'] = 'uz'
    live = context(live=True)
    held, counts = {}, {'toggle': 0, 'save': 0, 'entry': 0}
    def mock(route):
        url = route.request.url
        if '/api/bootstrap' in url:
            route.fulfill(json=fixture)
        elif '/api/settings' in url:
            kind = 'toggle' if set(route.request.post_data_json) == {'offline'} else 'save'
            counts[kind] += 1
            held[kind] = route
        elif '/toggle' in url:
            assert route.request.post_data_json == {'is_enabled': False}
            counts['entry'] += 1
            held['entry'] = route
        else:
            route.fulfill(json={'incoming': 0, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': 0, 'series': None})
    live.route('**/api/**', mock)
    app = new_page(live)
    app.goto(BASE + '/#replies')
    switch = app.locator('[data-setting=offline]')
    expect(switch).not_to_be_checked()
    switch.locator('xpath=..').click()
    language(app, 'en')
    expect(switch).to_be_checked()
    expect(switch).to_be_disabled()
    navigate(app, 'settings', '#connection-form')
    navigate(app, 'replies', '[name=auto_reply_text]')
    expect(switch).to_be_checked()
    expect(switch).to_be_disabled()
    switch.dispatch_event('change')
    assert counts['toggle'] == 1
    held.pop('toggle').fulfill(status=503, json={'detail': 'Temporary failure'})
    expect(switch).to_be_enabled()
    expect(switch).not_to_be_checked()
    switch.locator('xpath=..').click()
    held.pop('toggle').fulfill(json={'ok': True})
    expect(switch).to_be_enabled()
    expect(switch).to_be_checked()

    app.locator('[name=auto_reply_text]').fill('Keep this pending save')
    app.locator('#settings-form [type=submit]').click()
    expect(app.locator('#settings-form [type=submit]')).to_be_disabled()
    navigate(app, 'sleep', '[name=sleep_reply_text]')
    expect(app.locator('#settings-form [type=submit]')).to_be_enabled()
    navigate(app, 'replies', '[name=auto_reply_text]')
    expect(app.locator('[name=auto_reply_text]')).to_have_value('Keep this pending save')
    expect(app.locator('#settings-form [type=submit]')).to_be_disabled()
    app.locator('#settings-form').dispatch_event('submit')
    assert counts['save'] == 1
    held.pop('save').fulfill(json={'ok': True})
    expect(app.locator('#settings-form [type=submit]')).to_be_enabled()

    navigate(app, 'faq', '[data-action=add-faq]')
    entry = app.locator('[data-toggle="faq:1"]')
    entry.locator('xpath=..').click()
    language(app, 'ru')
    expect(entry).not_to_be_checked()
    expect(entry).to_be_disabled()
    held.pop('entry').fulfill(json={'is_enabled': True})
    expect(entry).to_be_checked()
    expect(entry).to_be_enabled()
    entry.locator('xpath=..').click()
    expect(entry).to_be_disabled()
    app.locator('[data-action="delete-faq:1"]').click()
    app.locator('[data-action="confirm-delete:faq:1"]').click()
    expect(app.locator('#modal')).not_to_be_visible()
    expect(entry).to_have_count(0)
    held.pop('entry').fulfill(json={'is_enabled': False})
    app.wait_for_timeout(150)
    expect(app.locator('#toast')).not_to_contain_text('Cannot')

    for failure in ['blocked', 'quota']:
        ctx = context()
        if failure == 'blocked':
            ctx.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new DOMException("Storage blocked","SecurityError")}})')
        else:
            ctx.add_init_script('Storage.prototype.setItem=function(){throw new DOMException("Quota exceeded","QuotaExceededError")}')
        page = new_page(ctx)
        page.goto(BASE + '/#replies')
        expect(page.locator('h1')).to_be_visible()
        language(page, 'en')
        expect(page.locator('#toast')).to_contain_text('only in this window')
        page.locator('[name=auto_reply_text]').fill('Session-only reply')
        page.locator('#settings-form [type=submit]').click()
        expect(page.locator('#toast')).to_contain_text('only in this window')
        page.locator('#theme-button').click()
        expect(page.locator('html')).to_have_class('dark')
        navigate(page, 'help', 'h1')
        expect(page.locator('#theme-button')).to_have_attribute('data-icon', 'sun')
        navigate(page, 'replies', '[name=auto_reply_text]')
        expect(page.locator('[name=auto_reply_text]')).to_have_value('Session-only reply')
        language(page, 'ru')
        expect(page.locator('#theme-button')).to_have_attribute('data-icon', 'sun')
        ctx.close()
    dark = context()
    dark.add_init_script('localStorage.setItem("ar-theme","dark")')
    page = new_page(dark)
    page.goto(BASE)
    expect(page.locator('#theme-button')).to_have_attribute('data-icon', 'sun')
    assert not errors, errors
    browser.close()
    print(json.dumps({'checks': ['pending toggle survives language/navigation', 'failed toggle rolls back and retries', 'pending save survives return without duplicate', 'entry toggle uses server result and tolerates deletion', 'blocked/quota storage session fallback', 'theme icon matches stored and current theme'], 'page_errors': errors}))
