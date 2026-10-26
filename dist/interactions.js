// Small, cancellable animations. Application state never waits on page transitions.
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const running = new Set();
const pageAnimations = new Set();
const closingDialogs = new WeakMap();
const menuAnimations = new WeakMap();
const mobileNavigations = new WeakMap();
const activeAnimations = new WeakMap();
const tokens = getComputedStyle(document.documentElement);
const timing = (name, fallback) => parseFloat(tokens.getPropertyValue(`--motion-${name}`)) || fallback;
const motion = {fast: timing('fast', 160), control: timing('control', 240), surface: timing('surface', 360), page: timing('page', 440), exit: timing('exit', 160)};
const ease = tokens.getPropertyValue('--motion-ease').trim() || 'cubic-bezier(.22,1,.36,1)';
const exitEase = tokens.getPropertyValue('--motion-exit-ease').trim() || 'cubic-bezier(.4,0,1,1)';
let previousPage;
let previousPeriod;

function visualState(el) {
  const style = getComputedStyle(el);
  return {opacity: style.opacity, transform: style.transform};
}

function animate(el, frames, options = {}) {
  if (reducedMotion.matches || !el?.animate || !el.isConnected) return null;
  const previous = activeAnimations.get(el);
  const originalWillChange = previous?.originalWillChange ?? el.style.willChange;
  previous?.animation.cancel();
  const hints = ['transform', 'opacity'].filter(key => frames.some(frame => key in frame));
  if (hints.length) el.style.willChange = hints.join(', ');
  const animation = el.animate(frames, {duration: motion.control, easing: ease, fill: 'both', ...options});
  activeAnimations.set(el, {animation, originalWillChange});
  running.add(animation);
  const cleanup = () => {
    running.delete(animation);
    if (activeAnimations.get(el)?.animation === animation) {
      el.style.willChange = originalWillChange;
      activeAnimations.delete(el);
    }
    animation.cancel();
  };
  animation.finished.then(cleanup, cleanup);
  return animation;
}

reducedMotion.addEventListener('change', event => {
  if (event.matches) for (const animation of running) animation.cancel();
});

export function animatePage(main, pageKey) {
  for (const animation of pageAnimations) animation.cancel();
  pageAnimations.clear();
  const selected = main.querySelector('[data-period].active');
  if (selected && selected.dataset.period !== previousPeriod) {
    previousPeriod = selected.dataset.period;
    animate(selected, [{transform: 'scale(.98)'}, {transform: 'scale(1)'}]);
  }
  if (pageKey === previousPage) return;
  previousPage = pageKey;
  for (const [index, child] of [...main.children].entries()) {
    if (child.getBoundingClientRect().top > innerHeight + 40) continue;
    const animation = animate(child, [
      {opacity: 0, transform: `translate3d(0,${index === 0 ? 8 : 14}px,0)`},
      {opacity: 1, transform: 'translate3d(0,0,0)'}
    ], {duration: motion.page, delay: Math.min(index, 3) * 28});
    if (animation) {
      pageAnimations.add(animation);
      animation.finished.then(() => pageAnimations.delete(animation), () => pageAnimations.delete(animation));
    }
  }
  for (const line of main.querySelectorAll('.chart-wrap polyline')) {
    const length = line.getTotalLength();
    // Keyframes leave no inline dash styles behind after completion/cancellation.
    const animation = animate(line, [
      {strokeDasharray: `${length}`, strokeDashoffset: length},
      {strokeDasharray: `${length}`, strokeDashoffset: 0}
    ], {duration: 600, delay: 60});
    if (animation) pageAnimations.add(animation);
  }
}

function positionMobileIndicator(nav, state, allowMotion = false) {
  if (!nav.getClientRects().length) {
    state.visible = false;
    state.indicator.hidden = true;
    state.animation?.cancel();
    return;
  }
  if (!state.visible) {
    state.visible = true;
    animate(nav, [
      {opacity: 0, transform: 'translate(-50%, 12px)'},
      {opacity: 1, transform: 'translate(-50%, 0)'}
    ], {duration: motion.surface});
  }
  const active = nav.querySelector('a.active');
  const indicator = state.indicator;
  if (!active) {
    indicator.hidden = true;
    state.animation?.cancel();
    state.key = null;
    return;
  }
  const container = nav.getBoundingClientRect();
  const rect = active.getBoundingClientRect();
  const x = rect.left - container.left - nav.clientLeft;
  const y = active.offsetTop;
  const width = active.offsetWidth;
  const height = active.offsetHeight;
  const target = `translate3d(${x}px, ${y}px, 0)`;
  const last = state.target;
  if (!indicator.hidden && state.key === active.hash && last && Math.abs(last.x - x) < .1 && last.y === y && last.width === width && last.height === height) return;
  const previous = indicator.hidden ? null : indicator.getBoundingClientRect();
  state.animation?.cancel();
  indicator.hidden = false;
  Object.assign(indicator.style, {transform: target, width: `${width}px`, height: `${height}px`});
  state.target = {x, y, width, height};
  if (allowMotion && previous && state.key !== active.hash) {
    state.animation = animate(indicator, [
      {transform: `translate3d(${previous.left - container.left - nav.clientLeft}px, ${y}px, 0) scaleX(${previous.width / width})`},
      {transform: `${target} scaleX(1)`}
    ], {duration: motion.surface});
  }
  state.key = active.hash;
}

export function updateMobileNavigation(nav, markup) {
  let state = mobileNavigations.get(nav);
  if (!state) {
    const indicator = document.createElement('span');
    indicator.className = 'mobile-nav-indicator';
    indicator.setAttribute('aria-hidden', 'true');
    indicator.hidden = true;
    nav.prepend(indicator);
    state = {indicator, visible: false, key: null, animation: null};
    mobileNavigations.set(nav, state);
    if (window.ResizeObserver) {
      state.observer = new ResizeObserver(() => positionMobileIndicator(nav, state));
      state.observer.observe(nav);
    } else window.addEventListener('resize', () => positionMobileIndicator(nav, state));
  }
  const template = document.createElement('template');
  template.innerHTML = markup;
  const existing = new Map([...nav.querySelectorAll('a')].map(link => [link.hash, link]));
  const retained = new Set();
  let index = 1;
  for (const next of template.content.querySelectorAll('a')) {
    const link = existing.get(next.hash) || next;
    // Keep nodes, focus and a running press effect during route/data updates.
    if (link.textContent !== next.textContent) link.innerHTML = next.innerHTML;
    link.classList.toggle('active', next.classList.contains('active'));
    if (next.classList.contains('active')) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
    retained.add(link.hash);
    if (nav.children[index] !== link) nav.insertBefore(link, nav.children[index] || null);
    index++;
  }
  for (const [key, link] of existing) if (!retained.has(key)) link.remove();
  positionMobileIndicator(nav, state, true);
}

export function showDialog(dialog) {
  closeLanguageMenus();
  const from = dialog.open ? visualState(dialog) : {opacity: 0, transform: 'translate3d(0,18px,0) scale(.985)'};
  dialog.style.setProperty('--backdrop-from', dialog.open ? getComputedStyle(dialog, '::backdrop').opacity : '0');
  const pending = closingDialogs.get(dialog);
  if (pending) { closingDialogs.delete(dialog); pending.cancel(); }
  delete dialog.dataset.closing;
  if (!dialog.open) dialog.showModal();
  animate(dialog, [
    from,
    {opacity: 1, transform: 'translate3d(0,0,0) scale(1)'}
  ], {duration: motion.surface});
}

export async function closeDialog(dialog) {
  if (!dialog.open || closingDialogs.has(dialog)) return;
  const from = visualState(dialog);
  dialog.style.setProperty('--backdrop-from', getComputedStyle(dialog, '::backdrop').opacity);
  // Retarget from the visible frame rather than jumping to a finished entrance.
  for (const animation of dialog.getAnimations()) animation.cancel();
  const animation = animate(dialog, [
    from,
    {opacity: 0, transform: 'translate3d(0,8px,0) scale(.992)'}
  ], {duration: motion.exit, easing: exitEase});
  if (!animation) { dialog.close(); return; }
  dialog.dataset.closing = 'true';
  closingDialogs.set(dialog, animation);
  await animation.finished.catch(() => {});
  if (closingDialogs.get(dialog) !== animation) return;
  closingDialogs.delete(dialog);
  delete dialog.dataset.closing;
  dialog.close();
}

export function animateSurface(el) {
  animate(el, [{opacity: 0, transform: 'translate3d(0,6px,0)'},
               {opacity: 1, transform: 'translate3d(0,0,0)'}], {duration: motion.control});
}

export function animateNotice(el) {
  animate(el, [
    visualState(el),
    {opacity: 1, transform: 'translate(-50%, 0)'}
  ], {duration: motion.surface});
}

function menuFor(trigger) { return document.getElementById(trigger.getAttribute('aria-controls')); }

function closeMenu(trigger, restoreFocus = false) {
  const menu = menuFor(trigger);
  if (!menu || menu.hidden || trigger.getAttribute('aria-expanded') === 'false') return;
  trigger.setAttribute('aria-expanded', 'false');
  const from = visualState(menu);
  const old = menuAnimations.get(menu);
  old?.cancel();
  const animation = animate(menu, [from, {opacity: 0, transform: `translate3d(0,${menu.closest('.opens-up') ? 3 : -3}px,0) scale(.992)`}], {duration: motion.exit, easing: exitEase});
  const finish = () => {
    if (menuAnimations.get(menu) !== animation) return;
    menu.hidden = true;
    menuAnimations.delete(menu);
  };
  menuAnimations.set(menu, animation);
  if (animation) animation.finished.then(finish, finish); else finish();
  if (restoreFocus) trigger.focus({preventScroll: true});
}

export function closeLanguageMenus() {
  document.querySelectorAll('[data-language-trigger][aria-expanded="true"]').forEach(trigger => closeMenu(trigger));
}

function openMenu(trigger, focus = 'selected') {
  closeLanguageMenus();
  const menu = menuFor(trigger);
  const from = menu.hidden ? null : visualState(menu);
  menuAnimations.get(menu)?.cancel();
  menuAnimations.delete(menu);
  menu.hidden = false;
  trigger.setAttribute('aria-expanded', 'true');
  const wrapper = trigger.closest('[data-language-switcher]');
  wrapper.classList.remove('opens-up');
  if (menu.getBoundingClientRect().bottom > innerHeight - 12) wrapper.classList.add('opens-up');
  const animation = animate(menu, [
    from || {opacity: 0, transform: `translate3d(0,${wrapper.classList.contains('opens-up') ? 5 : -5}px,0) scale(.985)`},
    {opacity: 1, transform: 'translate3d(0,0,0) scale(1)'}
  ], {duration: motion.surface});
  menuAnimations.set(menu, animation);
  const options = [...menu.querySelectorAll('[data-language-option]')];
  const target = focus === 'first' ? options[0] : focus === 'last' ? options.at(-1)
    : options.find(option => option.getAttribute('aria-checked') === 'true');
  target?.focus({preventScroll: true});
}

const pressTargets = 'button,.button,.quick-item,.mobile-nav a,#navigation a,.help-link,.avatar,.brand,.upgrade a';

function pressFeedback(target, point) {
  if (!target || target.matches(':disabled,[aria-disabled="true"],[aria-busy="true"]') || reducedMotion.matches) return;
  const bounds = target.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  target.querySelectorAll(':scope > .tap-wave').forEach(wave => wave.remove());
  const wave = document.createElement('span');
  wave.className = 'tap-wave';
  wave.setAttribute('aria-hidden', 'true');
  const size = Math.max(bounds.width, bounds.height) * 2;
  Object.assign(wave.style, {width: `${size}px`, height: `${size}px`, left: `${point ? point.clientX - bounds.left : bounds.width / 2}px`, top: `${point ? point.clientY - bounds.top : bounds.height / 2}px`});
  target.classList.add('tap-target');
  target.append(wave);
  const animation = animate(wave, [
    {opacity: .095, transform: 'translate(-50%,-50%) scale(.08)'},
    {opacity: 0, transform: 'translate(-50%,-50%) scale(1)'}
  ], {duration: 420, easing: ease});
  if (animation) animation.finished.then(() => wave.remove(), () => wave.remove()); else wave.remove();
}

export function initInteractions({changeLanguage, reportError}) {
  document.addEventListener('change', event => {
    if (!event.target.matches('.day-picker input,.role-option input')) return;
    animate(event.target.nextElementSibling, [{transform: 'scale(.975)'}, {transform: 'scale(1)'}]);
  });
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('[data-language-switcher]')) closeLanguageMenus();
    if (event.button !== 0 || !event.isPrimary) return;
    pressFeedback(event.target.closest(pressTargets), event);
  });

  document.addEventListener('click', async event => {
    // Keyboard and assistive activation get the same feedback, centered.
    if (event.detail === 0) pressFeedback(event.target.closest(pressTargets));
    const trigger = event.target.closest('[data-language-trigger]');
    if (trigger) {
      if (trigger.getAttribute('aria-expanded') === 'true') closeMenu(trigger, true); else openMenu(trigger);
      return;
    }
    const option = event.target.closest('[data-language-option]');
    if (!option) return;
    const ownerId = option.dataset.languageOwner;
    const owner = document.getElementById(ownerId);
    closeMenu(owner);
    try { await changeLanguage(option.dataset.languageOption); }
    catch (error) { reportError(error.message); }
    document.getElementById(ownerId)?.focus({preventScroll: true});
  });

  document.addEventListener('keydown', event => {
    const trigger = event.target.closest('[data-language-trigger]');
    const option = event.target.closest('[data-language-option]');
    if (trigger && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      openMenu(trigger, event.key === 'ArrowDown' ? 'first' : 'last');
    } else if (option) {
      const menu = option.closest('[role=menu]');
      const options = [...menu.querySelectorAll('[data-language-option]')];
      const index = options.indexOf(option);
      const destinations = {ArrowDown: (index + 1) % options.length, ArrowUp: (index + options.length - 1) % options.length, Home: 0, End: options.length - 1};
      if (event.key in destinations) {
        event.preventDefault();
        options[destinations[event.key]].focus({preventScroll: true});
      } else if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu(document.getElementById(option.dataset.languageOwner), true);
      } else if (event.key === 'Tab') closeLanguageMenus();
    } else if (trigger && event.key === 'Escape') closeMenu(trigger, true);
  });

  document.addEventListener('focusin', event => {
    document.querySelectorAll('[data-language-trigger][aria-expanded="true"]').forEach(trigger => {
      if (!trigger.closest('[data-language-switcher]').contains(event.target)) closeMenu(trigger);
    });
  });
}
