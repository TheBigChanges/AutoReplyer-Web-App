"""Exercise navigation, custom language menus, modal focus and reduced motion."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
Path('artifacts').mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE', '/usr/bin/google-chrome'), headless=True, args=['--no-sandbox'])
    errors = []
    context = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
    context.route('https://telegram.org/**', lambda route: route.fulfill(body=STUB, content_type='application/javascript'))
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE)
    trigger = page.locator('#header-language')
    trigger.focus()
    page.keyboard.press('ArrowDown')
    expect(trigger).to_have_attribute('aria-expanded', 'true')
    expect(page.locator('[data-language-owner=header-language][data-language-option=uz]')).to_be_focused()
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    expect(page.locator('#header-language')).to_have_attribute('data-current-language', 'ru')
    expect(page.locator('#header-language')).to_be_focused()
    page.keyboard.press('ArrowUp')
    expect(page.locator('[data-language-owner=header-language][data-language-option=en]')).to_be_focused()
    page.keyboard.press('Home')
    expect(page.locator('[data-language-owner=header-language][data-language-option=uz]')).to_be_focused()
    page.keyboard.press('End')
    page.keyboard.press('Escape')
    expect(page.locator('#header-language')).to_be_focused()
    expect(page.locator('#header-language-menu')).to_be_hidden()
    page.locator('#header-language').click()
    page.locator('h1').click()
    expect(page.locator('#header-language-menu')).to_be_hidden()
    page.locator('#header-language').click()
    page.keyboard.press('Tab')
    expect(page.locator('#header-language-menu')).to_be_hidden()

    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({'width': width, 'height': 900})
        page.locator('#header-language').click()
        menu = page.locator('#header-language-menu')
        expect(menu).to_be_visible()
        page.wait_for_timeout(190)
        rect = menu.bounding_box()
        assert rect['x'] >= 0 and rect['x'] + rect['width'] <= width, (width, rect)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.keyboard.press('Escape')
        expect(menu).to_be_hidden()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(BASE + '/#settings')
    page.locator('#settings-language').click()
    expect(page.locator('#settings-language-menu [aria-checked=true]')).to_have_attribute('data-language-option', 'ru')
    page.keyboard.press('Escape')
    page.locator('#header-language').click()
    page.locator('#header-language-menu [data-language-option=uz]').click()

    # Opening the reply preview must not accidentally submit and save its parent form.
    page.goto(BASE + '/#replies')
    original = page.locator('[name=auto_reply_text]').input_value()
    page.locator('[name=auto_reply_text]').fill('Unsaved draft to preserve')
    page.locator('[data-action=test]').click()
    expect(page.locator('#modal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#modal')).not_to_be_visible()
    expect(page.locator('[data-action=test]')).to_be_focused()
    assert page.locator('[name=auto_reply_text]').input_value() == 'Unsaved draft to preserve'
    page.reload()
    assert page.locator('[name=auto_reply_text]').input_value() == original

    # Fast route changes must leave the last requested screen usable.
    page.evaluate("location.hash='faq'; setTimeout(()=>location.hash='ai',15); setTimeout(()=>location.hash='scheduler',30)")
    expect(page.locator('h1')).to_have_text('Smart jadval')
    page.locator('[data-action=add-schedule]').click()
    expect(page.locator('#entry-form')).to_be_visible()
    page.locator('[data-action=close-modal]').first.click()
    expect(page.locator('#modal')).not_to_be_visible()
    page.wait_for_timeout(450)
    assert page.locator('.tap-wave').count() == 0

    # Check live save feedback while the response is intentionally held.
    page.goto(BASE + '/#dashboard')
    page.locator('[data-setting=offline]').first.locator('xpath=..').click()
    fixture = page.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    fixture['language'] = 'uz'
    fixture['user'] = {'id': 123, 'first_name': 'Test'}
    live_context = browser.new_context(locale='uz-UZ', viewport={'width': 390, 'height': 844})
    live_context.route('https://telegram.org/**', lambda route: route.fulfill(body=STUB.replace('initData:""', 'initData:"test-session"'), content_type='application/javascript'))
    held = []
    def api_mock(route):
        if '/api/bootstrap' in route.request.url:
            route.fulfill(json=fixture)
        elif '/api/analytics' in route.request.url:
            route.fulfill(json={'incoming': 0, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': 0, 'series': None})
        else:
            held.append(route)
    live_context.route('**/api/**', api_mock)
    live = live_context.new_page()
    live.on('pageerror', lambda error: errors.append(str(error)))
    live.goto(BASE + '/#replies')
    save = live.locator('#settings-form [type=submit]')
    save.click()
    expect(save).to_have_attribute('aria-busy', 'true')
    expect(save).to_be_disabled()
    live.wait_for_timeout(50)
    assert held
    held.pop().fulfill(json={'ok': True})
    expect(save).not_to_have_attribute('aria-busy', 'true')
    expect(save).to_be_enabled()

    # Respect OS accessibility preference, including when it changes at runtime.
    page.emulate_media(reduced_motion='reduce')
    page.goto(BASE + '/#faq')
    page.locator('[data-action=add-faq]').click()
    expect(page.locator('#modal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#modal')).not_to_be_visible()
    page.locator('#header-language').click()
    expect(page.locator('#header-language-menu')).to_be_visible()
    page.wait_for_timeout(30)
    assert page.evaluate('document.getAnimations().filter(a=>a.playState==="running").length') == 0
    assert page.locator('.tap-wave').count() == 0
    page.keyboard.press('Escape')
    page.emulate_media(reduced_motion='no-preference')
    page.goto(BASE + '/#dashboard')
    page.wait_for_timeout(600)
    page.locator('#header-language').click()
    page.wait_for_timeout(220)
    page.screenshot(path='artifacts/language-switcher-desktop.png')
    page.keyboard.press('Escape')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#theme-button').click()
    page.locator('#header-language').click()
    page.wait_for_timeout(220)
    page.screenshot(path='artifacts/language-switcher-mobile-dark.png')
    assert not errors, errors
    browser.close()
    print(json.dumps({'checks': ['keyboard menu and focus', 'outside and Escape dismissal', '4 viewport menu bounds', 'draft safety', 'rapid navigation', 'save loading state', 'reduced motion', 'ripple cleanup'], 'page_errors': errors}))
