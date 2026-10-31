"""Animation interruption, settled layout and compositor-hint cleanup regressions."""
import json
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AR_BASE_URL', 'http://127.0.0.1:8765')
STUB = 'window.Telegram={WebApp:{initData:"",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};'

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('AR_BROWSER_EXECUTABLE', '/usr/bin/google-chrome'), headless=True, args=['--no-sandbox'])
    context = browser.new_context(locale='uz-UZ', viewport={'width': 390, 'height': 844})
    context.route('https://telegram.org/**', lambda route: route.fulfill(body=STUB, content_type='application/javascript'))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE)
    expect(page.locator('h1')).to_be_visible()
    page.wait_for_timeout(750)

    # Reverse an entrance and then its exit in one frame. Neither direction may jump.
    deltas = page.evaluate('''() => {
      const trigger = document.querySelector('#header-language');
      const menu = document.querySelector('#header-language-menu');
      const state = () => {
        const style = getComputedStyle(menu);
        return [Number(style.opacity), new DOMMatrixReadOnly(style.transform).m42];
      };
      const step = () => { const a = menu.getAnimations()[0]; a.pause(); a.currentTime = a.effect.getTiming().duration * .3; };
      trigger.click(); step();
      const opening = state();
      trigger.click();
      const closingStart = state();
      step();
      const closing = state();
      trigger.click();
      const reopening = state();
      return [opening.map((v,i)=>Math.abs(v-closingStart[i])), closing.map((v,i)=>Math.abs(v-reopening[i]))];
    }''')
    assert all(delta[0] < .02 and delta[1] < .2 for delta in deltas), deltas
    page.wait_for_timeout(450)
    expect(page.locator('#header-language-menu')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#header-language-menu')).to_be_hidden()

    page.goto(BASE + '/#faq')
    expect(page.locator('[data-action=add-faq]')).to_be_visible()
    deltas = page.evaluate('''async () => {
      const {showDialog, closeDialog} = await import('/interactions.js');
      const dialog = document.querySelector('#modal');
      const state = () => {
        const s = getComputedStyle(dialog);
        return [Number(s.opacity), new DOMMatrixReadOnly(s.transform).m42];
      };
      const step = () => {
        const a = dialog.getAnimations().find(a => a.effect.target === dialog && !a.animationName);
        a.pause(); a.currentTime = a.effect.getTiming().duration * .25;
      };
      document.querySelector('[data-action=add-faq]').click(); step();
      const first = state();
      void closeDialog(dialog);
      const second = state();
      step();
      const third = state();
      showDialog(dialog);
      const fourth = state();
      return [first.map((v,i)=>Math.abs(v-second[i])), third.map((v,i)=>Math.abs(v-fourth[i]))];
    }''')
    assert all(delta[0] < .02 and delta[1] < .2 for delta in deltas), deltas
    page.wait_for_timeout(500)
    expect(page.locator('#modal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#modal')).not_to_be_visible()

    # A click animates the replacement theme SVG; keyboard gets the same effect.
    for activation in ['pointer', 'keyboard']:
        theme = page.locator('#theme-button')
        if activation == 'pointer': theme.click()
        else:
            theme.focus();page.keyboard.press('Enter')
        effect = page.locator('#theme-button svg').evaluate("""el => {
          const animation = el.getAnimations().find(a => a.effect.getKeyframes().some(f => 'scale' in f));
          if (!animation) return null;
          animation.pause();animation.currentTime = animation.effect.getTiming().duration * .25;
          const s = getComputedStyle(el), bounds = el.parentElement.getBoundingClientRect();
          return {scale:Number(s.scale),rotate:parseFloat(s.rotate),width:bounds.width,height:bounds.height};
        }""")
        assert effect and .89 <= effect['scale'] < 1 and abs(effect['rotate']) <= 5, effect
        assert effect['width'] >= 31 and effect['height'] >= 31,effect
        page.locator('#theme-button svg').evaluate('el => el.getAnimations().forEach(a=>a.play())')
        page.wait_for_timeout(350)
        assert page.locator('#theme-button svg').evaluate('el=>el.getAnimations().length') == 0
    # Rapid presses retarget smoothly and release all animation resources.
    page.evaluate("document.querySelector('#header-language').click(); document.querySelector('#header-language').click(); document.querySelector('#header-language').click()")
    page.wait_for_timeout(500)
    page.keyboard.press('Escape');expect(page.locator('#header-language-menu')).to_be_hidden()

    # Frosted floating layers use stronger fixed radii, with an opaque opt-out.
    assert page.locator('.topbar').evaluate('el=>getComputedStyle(el).backdropFilter') == 'none'
    assert page.locator('.topbar').evaluate("el=>getComputedStyle(el,'::before').backdropFilter") == 'blur(26px)'
    assert page.locator('.mobile-nav').evaluate('el=>getComputedStyle(el).backdropFilter').startswith('blur(33px)')
    page.locator('#header-language').click()
    assert page.locator('#header-language-menu').evaluate('el=>getComputedStyle(el).backdropFilter').startswith('blur(36px)')
    page.keyboard.press('Escape');expect(page.locator('#header-language-menu')).to_be_hidden()
    page.locator('[data-action=add-faq]').click()
    assert page.locator('#modal').evaluate("el=>getComputedStyle(el,'::backdrop').backdropFilter") == 'blur(13px)'
    page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
    cdp = context.new_cdp_session(page)
    cdp.send('Emulation.setEmulatedMedia', {'features':[{'name':'prefers-reduced-transparency','value':'reduce'}]})
    assert page.locator('.mobile-nav').evaluate('el=>getComputedStyle(el).backdropFilter') == 'none'
    assert page.locator('.topbar').evaluate("el=>getComputedStyle(el,'::before').backdropFilter") == 'none'
    cdp.send('Emulation.setEmulatedMedia', {'features':[]})
    cdp.detach()

    # Frequent route updates should settle precisely under the final tab.
    page.evaluate("location.hash='dashboard'; setTimeout(()=>location.hash='replies',35); setTimeout(()=>location.hash='faq',70); setTimeout(()=>location.hash='dashboard',105)")
    page.wait_for_timeout(850)
    bounds = page.evaluate('''() => {
      const a = document.querySelector('.mobile-nav a.active').getBoundingClientRect();
      const b = document.querySelector('.mobile-nav-indicator').getBoundingClientRect();
      return [Math.abs(a.left-b.left),Math.abs(a.top-b.top),Math.abs(a.width-b.width),Math.abs(a.height-b.height)];
    }''')
    assert max(bounds) < 1, bounds
    assert page.evaluate("[...document.querySelectorAll('*')].filter(el=>el.style.willChange).length") == 0
    assert page.evaluate('document.getAnimations().length') == 0
    assert page.locator('.tap-wave').count() == 0

    # A runtime accessibility change must cancel effects and leave controls usable.
    page.evaluate("document.querySelector('#header-language').click()")
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_timeout(80)
    page.locator('#theme-button').click()
    assert page.locator('#theme-button svg').evaluate('el=>el.getAnimations().length') == 0
    assert page.evaluate('document.getAnimations().length') == 0
    page.keyboard.press('Escape')
    expect(page.locator('#header-language-menu')).to_be_hidden()
    assert page.evaluate("[...document.querySelectorAll('*')].filter(el=>el.style.willChange).length") == 0
    assert not errors, errors
    print(json.dumps({'checks': ['menu reversal continuity', 'dialog reversal continuity', 'rapid dock settling', 'animation and layer cleanup', 'runtime reduced motion', 'pointer and keyboard icon press', 'rapid icon cleanup', 'stronger glass and reduced transparency'], 'page_errors': errors}))
    browser.close()
