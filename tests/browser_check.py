"""Manual QA runner. Uses installed Chrome; no browser download needed."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

artifacts = Path('artifacts')
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE', '/usr/bin/google-chrome'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1, locale='uz-UZ')
    base_url = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    # Offline-safe SDK stub, no Telegram account or credentials used in QA.
    page.route('https://telegram.org/**', lambda route: route.fulfill(status=200, body='window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};', content_type='application/javascript'))
    page.goto(base_url, wait_until='networkidle')
    page.screenshot(path=str(artifacts / 'desktop.png'), full_page=True)
    assert page.locator('h1').inner_text().startswith('Salom')
    for route in ['replies', 'ai', 'faq', 'knowledge', 'scheduler', 'analytics', 'sleep', 'profile', 'plans', 'settings', 'help']:
        page.goto(f'{base_url}/#{route}')
        page.wait_for_timeout(80)
        assert page.locator('h1').count() == 1, route
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'desktop overflow: {route}'
    page.goto(base_url + '/#faq')
    page.get_by_role('button', name='Savol qo‘shish', exact=True).click()
    page.locator('#entry-form [name=title]').fill('Test savol')
    page.locator('#entry-form [name=keywords]').fill('test, sinov')
    page.locator('#entry-form [name=content]').fill('Sinov javobi')
    page.locator('#entry-form [type=submit]').click()
    expect(page.get_by_role('heading', name='Test savol', exact=True)).to_have_count(1)
    page.locator('#entry-search').fill('topilmaydigan')
    assert page.locator('#no-results').is_visible()
    page.goto(base_url + '/#replies')
    page.locator('[name=auto_reply_text]').fill('Sinov uchun yangi matn')
    page.locator('#settings-form [type=submit]').click()
    page.reload()
    assert page.locator('[name=auto_reply_text]').input_value() == 'Sinov uchun yangi matn'
    page.goto(base_url + '/#scheduler')
    page.get_by_role('button', name='Jadval qo‘shish', exact=True).click()
    page.locator('#entry-form [type=submit]').click()
    assert 'kesishadi' in page.locator('#form-error').inner_text()
    page.get_by_role('button', name='Bekor qilish', exact=True).click()
    page.goto(base_url + '/#dashboard')
    page.get_by_role('button', name='Javobni sinash', exact=True).click()
    page.locator('#test-form [name=message]').fill('Ish vaqti qanday?')
    page.locator('#test-form [type=submit]').click()
    assert 'Smart FAQ' in page.locator('#test-result').inner_text()
    page.get_by_role('button', name='Yopish', exact=True).click()
    for width in [390, 320, 768]:
        page.set_viewport_size({'width': width, 'height': 844})
        for route in ['dashboard', 'replies', 'ai', 'faq', 'knowledge', 'scheduler', 'analytics', 'sleep', 'profile', 'plans', 'settings', 'help']:
            page.goto(f'{base_url}/#{route}')
            page.wait_for_timeout(50)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'overflow {width}: {route}'
    page.evaluate('localStorage.clear()')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(base_url + '/#dashboard')
    page.reload()
    page.screenshot(path=str(artifacts / 'mobile.png'), full_page=True)
    page.locator('#theme-button').click()
    assert page.locator('html').evaluate('(el)=>el.classList.contains("dark")')
    assert not errors, errors
    browser.close()
    print(json.dumps({'routes_checked': 12, 'viewport_widths': [1440, 768, 390, 320], 'checks': ['FAQ create and search', 'reply persistence', 'schedule conflict', 'FAQ preview', 'dark theme'], 'page_errors': errors}))

