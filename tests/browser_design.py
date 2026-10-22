"""Premium design: responsive controls, theme contrast and native chrome colors."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
ROUTES = ['dashboard', 'replies', 'ai', 'faq', 'knowledge', 'scheduler', 'analytics', 'sleep', 'profile', 'plans', 'settings', 'help']
STUB = '''window.chromeColors={};window.Telegram={WebApp:{initData:"",ready(){},expand(){},
setHeaderColor(c){window.chromeColors.header=c},setBackgroundColor(c){window.chromeColors.background=c}}};'''
Path('artifacts').mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    context = browser.new_context(locale='uz-UZ', viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    context.route('https://telegram.org/**', lambda route: route.fulfill(body=STUB, content_type='application/javascript'))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE)
    expect(page.locator('h1')).to_be_visible()
    assert page.locator('link[href="premium.css"]').count() == 1
    contrast = []
    combinations = 0
    for theme in ['light', 'dark']:
        if theme == 'dark':
            page.locator('#theme-button').click()
        ratios = page.evaluate('''() => {
          const s = getComputedStyle(document.documentElement);
          const rgb = value => {
            const el=document.createElement('span'); el.style.color=value; document.body.append(el);
            const channels=getComputedStyle(el).color.match(/[\\d.]+/g).slice(0,3).map(Number); el.remove();
            return channels.map(v => (v/=255)<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
          };
          const light = color => {const c=rgb(color); return .2126*c[0]+.7152*c[1]+.0722*c[2]};
          const ratio = (a,b) => {a=light(s.getPropertyValue(a));b=light(s.getPropertyValue(b));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
          return [ratio('--ink','--surface'),ratio('--muted','--surface'),ratio('--green','--mint')];
        }''')
        assert min(ratios) >= 4.5, (theme, ratios)
        contrast.append({'theme': theme, 'ratios': ratios})
        assert page.evaluate('''() => {
          const s=getComputedStyle(document.documentElement);
          return chromeColors.header===s.getPropertyValue('--surface').trim() &&
            chromeColors.background===s.getPropertyValue('--bg').trim() &&
            document.querySelector('meta[name="theme-color"]').content===chromeColors.background;
        }''')
        for language in ['uz', 'ru', 'en']:
            trigger=page.locator('#header-language')
            if trigger.get_attribute('data-current-language') != language:
                trigger.click()
                page.locator(f'#header-language-menu [data-language-option={language}]').click()
            for width in [1440, 768, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 900})
                for route in ROUTES:
                    page.goto(BASE + '/#' + route)
                    expect(page.locator('h1')).to_be_visible()
                    result = page.evaluate('''() => {
                      const invalid = [...document.querySelectorAll('#main .button,#main input:not([type=checkbox]):not([type=radio]),#main textarea,#main select')]
                        .filter(el => el.getClientRects().length)
                        .filter(el => {const r=el.getBoundingClientRect();return r.left < -1 || r.right > innerWidth+1 || el.scrollWidth > el.clientWidth+2})
                        .map(el => el.outerHTML.slice(0,180));
                      return {overflow:document.documentElement.scrollWidth>innerWidth,invalid};
                    }''')
                    assert not result['overflow'] and not result['invalid'], (theme, language, width, route, result)
                    combinations += 1
        # Capture both themes after all effects settle, with the dock clearly visible.
        page.goto(BASE + '/#dashboard')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=f'artifacts/premium-final-mobile-{theme}.png', full_page=True)
        page.goto(BASE + '/#replies')
        page.screenshot(path=f'artifacts/premium-final-replies-{theme}.png', full_page=True)
        page.goto(BASE + '/#faq')
        page.locator('[data-action=add-faq]').click()
        expect(page.locator('#modal')).to_be_visible()
        box=page.locator('#modal').bounding_box()
        assert box['x'] >= 0 and box['x']+box['width'] <= 390
        page.screenshot(path=f'artifacts/premium-final-dialog-{theme}.png')
        page.keyboard.press('Escape')
        expect(page.locator('#modal')).not_to_be_visible()
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.goto(BASE + '/#plans')
        page.screenshot(path=f'artifacts/premium-final-plans-{theme}.png', full_page=True)
        page.goto(BASE + '/#dashboard')
        page.screenshot(path=f'artifacts/premium-final-desktop-{theme}.png', full_page=True)
    assert not errors, errors
    print(json.dumps({'layout_combinations':combinations,'checks':['all routes, languages and themes','controls fit at four widths','readable core text contrast','Telegram and browser theme colors','mobile dialog bounds'],'contrast':contrast,'page_errors':errors}))
    browser.close()
