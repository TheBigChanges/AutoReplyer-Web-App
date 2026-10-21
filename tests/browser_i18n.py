"""Three-language UI, persistence and content isolation checks in real Chrome."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
ROUTES = ['dashboard', 'replies', 'ai', 'faq', 'knowledge', 'scheduler', 'analytics', 'sleep', 'profile', 'plans', 'settings', 'help']
LABELS = {
    'uz': ['Salom', 'Avtojavob', 'AI yordamchi', 'Smart FAQ', 'Bilimlar bazasi', 'Smart jadval', 'Statistika', 'Uyqu rejimi', 'Profil vositalari', 'Sizga mos tarif', 'Sozlamalar', 'Boshlash oson'],
    'ru': ['Здравствуйте', 'Автоответ', 'ИИ-помощник', 'Smart FAQ', 'База знаний', 'Умное расписание', 'Статистика', 'Режим сна', 'Инструменты профиля', 'Тариф для вас', 'Настройки', 'Начать просто'],
    'en': ['Hello', 'Auto-reply', 'AI assistant', 'Smart FAQ', 'Knowledge base', 'Smart scheduler', 'Analytics', 'Sleep mode', 'Profile tools', 'Your ideal plan', 'Settings', 'Getting started is easy'],
}
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'
Path('artifacts').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    context = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000})
    context.route('https://telegram.org/**', lambda route: route.fulfill(status=200, body=STUB, content_type='application/javascript'))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.locator('#header-language').wait_for()
    # Language changes preserve unsaved inputs and their preview, without saving a reply.
    page.goto(BASE + '/#replies')
    original = page.locator('[name=auto_reply_text]').input_value()
    draft = 'Keep this original user text: Привет, salom, hello <safe>'
    page.locator('[name=auto_reply_text]').fill(draft)
    page.locator('#header-language').select_option('ru')
    assert page.locator('[name=auto_reply_text]').input_value() == draft
    assert page.locator('#reply-preview').inner_text() == draft
    page.reload()
    assert page.locator('[name=auto_reply_text]').input_value() == original
    assert page.locator('#header-language').input_value() == 'ru'
    for language in ['uz', 'ru', 'en']:
        page.locator('#header-language').select_option(language)
        for width in [1440, 768, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 900})
            for route, heading in zip(ROUTES, LABELS[language]):
                page.goto(f'{BASE}/#{route}')
                page.wait_for_timeout(20)
                assert page.locator('html').get_attribute('lang') == language
                assert page.locator('h1').inner_text().startswith(heading), (language, route)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, route)
                assert page.locator('#header-language').input_value() == language
                if route == 'settings':
                    assert page.locator('#settings-language').input_value() == language
                # Application text must not expose unresolved interpolation placeholders.
                assert not page.locator('#main').evaluate('(el)=>/\\{\\d+\\}/.test(el.innerText)'), (language, route)
        if language != 'uz':
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.goto(BASE + '/#dashboard')
            page.screenshot(path=f'artifacts/desktop-{language}.png', full_page=True)
    page.goto(BASE + '/#settings')
    page.locator('#settings-language').select_option('ru')
    assert page.locator('#header-language').input_value() == 'ru'
    page.goto(BASE + '/#scheduler')
    page.locator('[data-action=add-schedule]').click()
    assert page.locator('.day-picker label').first.inner_text() == 'Пн'
    page.locator('#entry-form [type=submit]').click()
    assert 'пересекается' in page.locator('#form-error').inner_text()
    page.locator('[data-action=close-modal]').first.click()
    # Persist a demo record so it can also serve as a complete mocked live bootstrap.
    page.goto(BASE + '/#dashboard')
    page.locator('[data-setting=offline]').first.locator('xpath=..').click()
    fixture = page.evaluate('JSON.parse(localStorage.getItem("ar-demo-v1"))')
    assert fixture['settings']['auto_reply_text'] == original
    fixture['language'] = 'ru'
    fixture['user'] = {'id': 123, 'first_name': 'Alex'}
    fixture['plan'] = 'free'
    fixture['settings']['ai_enabled'] = False
    live_context = browser.new_context(locale='en-US', viewport={'width': 390, 'height': 844})
    live_stub = STUB.replace('initData:""', 'initData:"test-session",initDataUnsafe:{user:{language_code:"en"}}')
    live_context.route('https://telegram.org/**', lambda route: route.fulfill(status=200, body=live_stub, content_type='application/javascript'))
    requests = []
    def api_mock(route):
        request = route.request
        requests.append({'path': request.url.split('/api/')[-1], 'language': request.headers.get('accept-language'), 'method': request.method})
        if '/api/bootstrap' in request.url:
            route.fulfill(json=fixture)
        elif '/api/analytics' in request.url:
            route.fulfill(json={'incoming': 0, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': None, 'series': None})
        else:
            route.fulfill(status=403, json={'detail': 'This feature requires a higher plan. Upgrade your plan in the bot.'})
    live_context.route('**/api/**', api_mock)
    live = live_context.new_page()
    live.on('pageerror', lambda error: errors.append(str(error)))
    live.goto(BASE)
    live.wait_for_function('document.documentElement.lang === "ru"')
    assert live.locator('h1').inner_text().startswith('Здравствуйте')
    live.locator('#header-language').select_option('en')
    assert all(r['method'] == 'GET' for r in requests), 'Changing language must not change bot settings.'
    live.reload()
    live.wait_for_function('document.querySelector("h1")?.textContent.startsWith("Hello")')
    assert live.locator('#header-language').input_value() == 'en'
    live.goto(BASE + '/#ai')
    live.locator('[data-setting=ai_enabled]').locator('xpath=..').click()
    expect(live.locator('#toast')).to_contain_text('higher plan')
    assert not live.locator('[data-setting=ai_enabled]').is_checked()
    assert requests[-1]['language'] == 'en'
    # Session errors must remain readable and let users choose a language.
    live_context.route('**/api/**', lambda route: route.fulfill(status=401, json={'detail': 'Expired'}))
    live.reload()
    live.get_by_role('heading', name='Could not connect to the API').wait_for()
    live.locator('#header-language').select_option('ru')
    assert live.get_by_role('heading', name='Не удалось подключиться к API').count() == 1
    assert not errors, errors
    browser.close()
    print(json.dumps({'languages': ['uz', 'ru', 'en'], 'routes': 12, 'widths': [1440, 768, 390, 320], 'checks': ['draft preservation', 'language persistence', 'bot-language default', 'no unintended bot writes', 'localized Free restriction', 'localized session error'], 'page_errors': errors}))
