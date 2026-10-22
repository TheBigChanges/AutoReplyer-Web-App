"""Back control: app history, safe deep-link fallback, languages and glass UI."""
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765').rstrip('/')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
Path('artifacts').mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    context = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
    context.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB, content_type='application/javascript'))
    context.add_init_script('history.replaceState({integrationState:"preserve"}, "")')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    def at(route):
        expect(page).to_have_url(re.compile(r'/#' + route + r'$'))
        expect(page.locator('h1')).to_be_visible()
    def visit(route):
        page.evaluate('(r)=>location.hash=r', route)
        at(route)
    def language(code):
        page.locator('#header-language').click()
        page.locator('#header-language-menu [data-language-option='+code+']').click()
        expect(page.locator('#header-language')).to_have_attribute('data-current-language', code)

    page.goto(BASE + '/#dashboard')
    back = page.locator('#back-button')
    expect(back).to_be_hidden()
    page.locator('#navigation [href="#replies"]').click()
    at('replies')
    page.locator('#navigation [href="#sleep"]').click()
    at('sleep')
    back.click()
    at('replies')
    back.focus()
    page.keyboard.press('Enter')
    at('dashboard')
    expect(back).to_be_hidden()
    page.go_forward()
    at('replies')
    page.go_forward()
    at('sleep')
    page.go_back()
    at('replies')
    visit('faq')  # A new branch after native Back must have the correct parent.
    back.click()
    at('replies')
    for code, label in [('ru', 'Назад'), ('en', 'Back'), ('uz', 'Orqaga')]:
        language(code)
        expect(back).to_have_attribute('aria-label', label)
        expect(back).to_have_attribute('title', label)
    back.click()
    at('dashboard')

    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({'width': width, 'height': 844})
        page.goto(BASE + '/#knowledge')
        at('knowledge')
        language('ru')
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_timeout(250)
        box = back.bounding_box()
        picker = page.locator('#header-language').bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] < picker['x']
        assert box['y'] >= 0 and box['y'] + box['height'] <= 844
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert 'blur(12px)' in back.evaluate('(n)=>getComputedStyle(n).backdropFilter')
        if width == 320:
            page.screenshot(path='artifacts/back-button-mobile-light.png')
            page.locator('#theme-button').click()
            page.wait_for_timeout(250)
            page.screenshot(path='artifacts/back-button-mobile-dark.png')
        back.click()
        at('dashboard')  # Deep links must stay within the app.
        expect(back).to_be_hidden()
        assert page.evaluate('history.state.integrationState') == 'preserve'
        page.reload()
        expect(back).to_be_hidden()

    visit('settings')
    page.reload()  # Reload starts a fresh app visit rather than trusting old history.
    expect(back).to_be_visible()
    back.click()
    at('dashboard')
    page.emulate_media(reduced_motion='reduce')
    visit('profile')
    page.wait_for_timeout(30)
    assert back.evaluate('(n)=>n.getAnimations({subtree:true}).length') == 0
    back.click()
    at('dashboard')
    assert not errors, errors
    browser.close()
    print(json.dumps({'checks': ['nested back', 'native Back/Forward and branch', 'keyboard activation', 'deep-link/reload fallback stays in app', 'history integration state preserved', '3 language labels', '4 viewport bounds', 'light/dark glass', 'reduced motion'], 'page_errors': errors}))
