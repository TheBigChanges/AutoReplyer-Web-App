"""Browser regressions for draft loss, delayed responses and credential routing."""
import json
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE', '/usr/bin/google-chrome'), headless=True, args=['--no-sandbox'])
    errors = []
    context = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
    context.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB, content_type='application/javascript'))
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE + '/#replies')
    draft = 'Unsaved <script>window.unexpected=true</script> draft'
    page.locator('[name=auto_reply_text]').fill(draft)
    page.locator('[data-setting=offline]').locator('xpath=..').click()
    expect(page.locator('#toast')).to_be_visible()
    expect(page.locator('[name=auto_reply_text]')).to_have_value(draft)
    expect(page.locator('#reply-preview')).to_have_text(draft)
    assert not page.evaluate('Boolean(window.unexpected)')
    fixture = page.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['user'] = {'id': 123, 'first_name': '<img src=x onerror="window.unexpected=true">'}
    fixture['language'] = 'uz'
    fixture['plan'] = 'ultra'

    live = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
    live.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB.replace('initData:""', 'initData:"fake-session"'), content_type='application/javascript'))
    held = {}
    counts = {'settings': 0, 'delete': 0}
    def analytics(n):
        return {'incoming': n, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': 0, 'series': None}
    def mock(route):
        url = route.request.url
        if '/api/bootstrap' in url:
            route.fulfill(json=fixture)
        elif '/api/analytics?days=7' in url:
            held['analytics'] = route
        elif '/api/analytics' in url:
            route.fulfill(json=analytics(30 if 'days=30' in url else 1))
        elif '/api/settings' in url:
            counts['settings'] += 1
            held['settings'] = route
        elif '/api/test' in url:
            held['preview'] = route
        elif route.request.method == 'DELETE':
            counts['delete'] += 1
            held['delete'] = route
        else:
            route.fulfill(json={'ok': True})
    live.route('**/api/**', mock)
    app = live.new_page()
    app.on('pageerror', lambda e: errors.append(str(e)))
    app.goto(BASE)
    expect(app.locator('h1')).to_contain_text('<img src=x')
    assert app.locator('h1 img').count() == 0
    assert not app.evaluate('Boolean(window.unexpected)')
    app.locator('[data-period="7"]').click()
    app.wait_for_timeout(60)
    assert 'analytics' in held
    app.locator('[data-period="30"]').click()
    expect(app.locator('[data-period="30"]')).to_have_class('active')
    held.pop('analytics').fulfill(json=analytics(7))
    app.wait_for_timeout(100)
    expect(app.locator('[data-period="30"]')).to_have_class('active')
    expect(app.locator('.stat-value').first).to_have_text('30')

    app.goto(BASE + '/#replies')
    app.locator('[name=auto_reply_text]').fill('Pending save draft')
    app.locator('#settings-form [type=submit]').click()
    expect(app.locator('#settings-form [type=submit]')).to_have_attribute('aria-busy', 'true')
    app.locator('#header-language').click()
    app.locator('#header-language-menu [data-language-option=en]').click()
    expect(app.locator('#settings-form [type=submit]')).to_be_disabled()
    app.locator('#settings-form').dispatch_event('submit')
    assert counts['settings'] == 1
    held.pop('settings').fulfill(json={'ok': True})
    expect(app.locator('#settings-form [type=submit]')).to_be_enabled()
    expect(app.locator('[name=auto_reply_text]')).to_have_value('Pending save draft')

    app.locator('[data-action=test]').click()
    app.locator('#test-form [name=message]').fill('Hello')
    app.locator('#test-form [type=submit]').click()
    app.keyboard.press('Escape')
    expect(app.locator('#modal')).not_to_be_visible()
    app.locator('[data-action=test]').click()
    app.locator('#test-form [name=message]').fill('New preview draft')
    held.pop('preview').fulfill(json={'source': 'old', 'text': 'Stale result'})
    app.wait_for_timeout(100)
    expect(app.locator('#test-form [name=message]')).to_have_value('New preview draft')
    expect(app.locator('#test-result')).to_be_empty()
    app.keyboard.press('Escape')
    expect(app.locator('#modal')).not_to_be_visible()

    app.goto(BASE + '/#faq')
    app.locator('[data-action^="delete-faq:"]').first.click()
    confirm = app.locator('[data-action^="confirm-delete:"]')
    confirm.click()
    expect(confirm).to_be_disabled()
    confirm.dispatch_event('click')
    assert counts['delete'] == 1
    app.keyboard.press('Escape')
    expect(app.locator('#modal')).not_to_be_visible()
    app.locator('[data-action=add-faq]').click()
    app.locator('#entry-form [name=title]').fill('New FAQ draft')
    held.pop('delete').fulfill(json={'ok': True})
    app.wait_for_timeout(100)
    expect(app.locator('#modal')).to_be_visible()
    expect(app.locator('#entry-form [name=title]')).to_have_value('New FAQ draft')
    app.keyboard.press('Escape')
    expect(app.locator('#modal')).not_to_be_visible()

    # A saved endpoint cannot select an origin that receives initData.
    app.evaluate('localStorage.setItem("ar-api", "https://attacker.invalid")')
    leaked = []
    app.on('request', lambda r: leaked.append(r.url) if r.url.startswith('https://attacker.invalid') else None)
    app.reload()
    expect(app.locator('h3')).to_contain_text('Could not connect to the API')
    assert not leaked

    # A hash change during verification must not expose editable seed controls.
    app.evaluate('localStorage.removeItem("ar-api")')
    live.route('**/api/bootstrap', lambda route: held.update(bootstrap=route))
    app.reload()
    expect(app.locator('#main')).to_contain_text('Verifying your Telegram account')
    app.evaluate("location.hash='ai'")
    expect(app.locator('#main')).to_contain_text('Verifying your Telegram account')
    assert app.locator('#settings-form').count() == 0
    held.pop('bootstrap').fulfill(json=fixture)
    expect(app.locator('#settings-form')).to_be_visible()
    live.unroute('**/api/bootstrap')
    live.route('**/api/analytics*', lambda route: route.fulfill(status=503, json={'detail': 'Analytics temporarily unavailable'}))
    app.goto(BASE)
    expect(app.locator('h1')).to_contain_text('Hello')
    expect(app.locator('#toast')).to_contain_text('Analytics temporarily unavailable')
    assert app.locator('[data-action=enter-demo]').count() == 0
    assert not errors, errors
    browser.close()
    print(json.dumps({'checks': ['toggle preserves draft and escaped preview', 'escaped Telegram name', 'latest analytics response wins', 'language switch preserves pending save and prevents duplicate', 'stale preview/delete cannot overwrite or close new dialog', 'saved untrusted API cannot receive session', 'loading navigation never exposes seed controls', 'analytics outage preserves authenticated account'], 'page_errors': errors}))
