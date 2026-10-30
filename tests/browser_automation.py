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
    fixture['language'] = 'uz'; fixture['plan'] = 'pro'
    fixture['automation'][0]['name'] = '<img src=x onerror=alert(1)>'
    context = browser.new_context(locale='uz-UZ', viewport={'width': 390, 'height': 844})
    context.route('https://telegram.org/**', lambda r: r.fulfill(body=STUB.replace('initData:""', 'initData:"signed-test"'), content_type='application/javascript'))
    writes = []; held = {}; hold = {'create': False, 'toggle': False, 'confirmation': False, 'edit': False, 'stats': False}; fail = {'toggle': False}; errors = []
    def api(route):
        path = route.request.url.split('/api/')[-1]
        method = route.request.method
        if path == 'bootstrap': route.fulfill(json=copy.deepcopy(fixture))
        elif path.startswith('analytics'): route.fulfill(json={'incoming': 0, 'sent': 0, 'kinds': {'ai': 0, 'faq': 0, 'static': 0, 'sleep': 0}, 'peak': None, 'skipped': None, 'series': None})
        elif path == 'automation':
            body = route.request.post_data_json; writes.append((path, body))
            assert set(body) == {'name', 'keywords', 'reply', 'priority', 'days', 'time_range'}
            conditions = [{'type':'keyword_any','value':body['keywords']}] if len(body['keywords']) > 1 else [{'type':'keyword_contains','value':body['keywords'][0]}]
            conditions += [{'type':kind,'value':body[key]} for key,kind in [('days','days_of_week'),('time_range','time_between')] if body[key] is not None]
            rule = {'id':99, 'name':body['name'], 'conditions':{'operator':'all','items':conditions}, 'action':{'type':'send_reply','text':body['reply']}, 'priority':body['priority'], 'is_enabled':True, 'sent_count':0, 'last_sent_at':None}
            fixture['automation'].append(rule)
            if hold['create']: held['create'] = (route, rule)
            else: route.fulfill(json=rule)
        elif path == 'automation/stats':
            stats = {'days':7, 'period_sent':8, 'all_sent':19, 'deleted_sent':11, 'counters_since':'2026-10-29T10:00:00Z', 'total_rules':len(fixture['automation']), 'enabled_rules':1, 'top':[{'id':99,'name':'<script>counter</script>','sent_count':8}]}
            if hold['stats']: held['stats'] = (route, stats)
            else: route.fulfill(json=stats)
        elif path.startswith('automation/') and method == 'PATCH':
            body = route.request.post_data_json; writes.append((path,body))
            assert set(body) <= {'name','keywords','reply','priority','days','time_range'}, body
            rule = next(r for r in fixture['automation'] if r['id'] == int(path.split('/')[1]))
            for key in ['name','priority']:
                if key in body: rule[key] = body[key]
            if 'reply' in body: rule['action']['text'] = body['reply']
            if 'keywords' in body:
                rule['conditions']['items'] = [c for c in rule['conditions']['items'] if c['type'] not in ['keyword_contains','keyword_any']]
                rule['conditions']['items'].insert(0,{'type':'keyword_any','value':body['keywords']} if len(body['keywords']) > 1 else {'type':'keyword_contains','value':body['keywords'][0]})
            for key,kind in [('days','days_of_week'),('time_range','time_between')]:
                if key in body:
                    rule['conditions']['items'] = [c for c in rule['conditions']['items'] if c['type'] != kind]
                    if body[key] is not None: rule['conditions']['items'].append({'type':kind,'value':body[key]})
            if hold['edit']: held['edit'] = (route, copy.deepcopy(rule))
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
    page.locator('input[name=keyword]').fill('delivery, shipping*, courier')
    page.locator('textarea[name=reply]').fill('Your original reply')
    page.locator('[name=automation_day][value="0"]').locator('xpath=..').click()
    page.locator('[name=automation_start]').fill('22:00')
    page.locator('[name=automation_end]').fill('06:00')
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
    expect(page.locator('.automation-rule').last).to_contain_text('delivery OR shipping* OR courier')
    # Edit keeps enabled state/counters; only the edited field is sent.
    fixture['automation'][-1]['sent_count'] = 8
    fixture['automation'][-1]['last_sent_at'] = '2026-10-29T10:00:00Z'
    fixture['automation'][-1]['is_enabled'] = False
    page.reload()
    page.locator('[data-action="edit-automation:99"]').click()
    expect(page.locator('[name=keyword]')).to_have_value('delivery, shipping*, courier')
    assert page.locator('[name=keyword]').evaluate('(el)=>getComputedStyle(el).borderRadius') == '11px'
    expect(page.locator('[name=automation_start]')).to_have_value('22:00')
    page.wait_for_timeout(400)
    page.screenshot(path=str(ARTIFACTS/'automation-v12-editor.png'),full_page=True)
    page.locator('[name=name]').fill('Edited delivery')
    page.locator('#automation-form [type=submit]').click()
    expect(page.locator('#automation-review')).to_be_visible()
    hold['edit'] = True
    page.locator('#automation-form [type=submit]').click()
    page.wait_for_timeout(100)
    expect(page.locator('#automation-form [type=submit]')).to_be_disabled()
    page.locator('#automation-form').evaluate('(el)=>el.requestSubmit()')
    assert writes[-1] == ('automation/99', {'name':'Edited delivery'}), writes
    assert len([w for w in writes if w[0] == 'automation/99']) == 1
    page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    page.locator('[data-action="edit-automation:99"]').click()
    expect(page.locator('#modal')).not_to_be_visible()
    page.locator('[data-toggle="automation:99"]').locator('xpath=..').click()
    expect(page.locator('[data-toggle="automation:99"]')).to_be_checked()
    r,rule = held.pop('edit'); r.fulfill(json=rule); hold['edit'] = False
    expect(page.locator('.automation-rule').last).to_contain_text('Edited delivery')
    expect(page.locator('[data-toggle="automation:99"]')).to_be_checked()
    expect(page.locator('.automation-counter').last).to_contain_text('8')
    fixture['automation'][-1]['is_enabled'] = True; page.reload()
    # Stats safely render names/counters in all locales and stay within the viewport.
    for lang,title in [('uz','Automation statistikasi'),('ru','Статистика автоматизации'),('en','Automation statistics')]:
        if page.locator('#header-language').get_attribute('data-current-language') != lang:
            page.locator('#header-language').click();page.locator(f'#header-language-menu [data-language-option={lang}]').click()
        page.locator('[data-action=automation-stats]').click()
        expect(page.locator('#modal h2')).to_have_text(title)
        if lang == 'en':
            page.wait_for_timeout(400)
            page.screenshot(path=str(ARTIFACTS/'automation-v12-stats.png'),full_page=True)
        expect(page.locator('.automation-top')).to_contain_text('<script>counter</script>')
        assert page.locator('.automation-top script').count() == 0
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':920})
            assert page.locator('#modal').evaluate('(el)=>el.scrollWidth <= el.clientWidth'), (lang,width)
        page.set_viewport_size({'width':390,'height':844})
        page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
    hold['stats'] = True
    page.locator('[data-action=automation-stats]').click();page.wait_for_timeout(100)
    page.locator('#mobile-nav a[href="#settings"]').click()
    r,stats = held.pop('stats');r.fulfill(json=stats);hold['stats'] = False
    expect(page.locator('#modal')).not_to_be_visible()
    page.locator('.mobile-sections a[href="#automation"]').click()
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
    assert not any(path == 'automation/99' and body == {'token':'t'*43} for path, body in writes)
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
    fixture['plan'] = 'plus'; page.reload()
    page.locator('[data-action=add-automation]').first.click()
    expect(page.locator('[name=automation_start]')).to_be_disabled()
    page.keyboard.press('Escape'); expect(page.locator('#modal')).not_to_be_visible()
    # Legacy single keywords may contain punctuation that looks like an OR delimiter.
    fixture['automation'][0]['conditions']['items'] = [{'type':'keyword_contains','value':'ish, vaqt'}]
    page.reload()
    page.locator('[data-action="edit-automation:1"]').click()
    page.locator('[name=name]').fill('Legacy punctuation')
    page.locator('#automation-form [type=submit]').click();page.locator('#automation-form [type=submit]').click()
    expect(page.locator('#modal')).not_to_be_visible()
    assert writes[-1] == ('automation/1', {'name':'Legacy punctuation'}), writes[-1]
    fixture['automation'][0]['conditions']['items'] = [{'type':'keyword_any','value':['narx*','price']},{'type':'days_of_week','value':[0]},{'type':'time_between','value':{'start':540,'end':1080}}]
    page.reload()
    page.locator('[data-action="edit-automation:1"]').click()
    page.locator('[name=name]').fill('Plus basic edit')
    page.locator('#automation-form [type=submit]').click();page.locator('#automation-form [type=submit]').click()
    expect(page.locator('#modal')).not_to_be_visible()
    assert writes[-1] == ('automation/1',{'name':'Plus basic edit'}), writes[-1]
    page.locator('[data-action="edit-automation:1"]').click()
    page.locator('[name=keyword]').fill('narx*')
    page.locator('[data-action="automation-clear:days"]').click()
    page.locator('[data-action="automation-clear:time_range"]').click()
    page.locator('#automation-form [type=submit]').click();page.locator('#automation-form [type=submit]').click()
    expect(page.locator('#modal')).not_to_be_visible()
    assert writes[-1] == ('automation/1',{'keywords':['narx*'],'days':None,'time_range':None}), writes[-1]
    # Maximum-length owner text wraps; invalid legacy timezone falls back safely.
    fixture['plan'] = 'pro'
    fixture['settings']['name_clock_tz'] = 'Invalid/Timezone'
    fixture['automation'][0]['name'] = 'A'*60
    fixture['automation'][0]['last_sent_at'] = '2026-10-29T10:00:00Z'
    fixture['automation'][0]['conditions']['items'] = [{'type':'keyword_any','value':[letter*50 for letter in 'abcde']}]
    page.reload()
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':920})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    page.set_viewport_size({'width':390,'height':844})
    page.locator('[data-action=automation-stats]').click()
    expect(page.locator('#modal h2')).to_have_text('Automation statistics')
    page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
    fixture['settings']['name_clock_tz'] = 'Asia/Tashkent'
    fixture['plan'] = 'free'; page.reload()
    expect(page.locator('[data-action=add-automation]')).to_have_count(0)
    expect(page.locator('[data-toggle^="automation:"]')).to_have_count(0)
    expect(page.locator('#main a[href="#plans"]').first).to_be_visible()
    assert not errors, errors
    print(json.dumps({'checks':['3 locales x 4 widths','escaped user text','review before enabled save','duplicate create prevention','pending toggle and failure recovery','owner token delete payload','stale confirmation navigation','Free lock','glass and reduced motion','v1.2 OR create and partial edit','held edit preserves counters','stats locales and stale response','Plus downgrade preserves or clears filters'], 'page_errors':errors}))
    browser.close()
