// Small, cancellable animations. Application state never waits on page transitions.
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const running = new Set();
const pageAnimations = new Set();
const closingDialogs = new WeakMap();
const menuAnimations = new WeakMap();
const ease = 'cubic-bezier(.2,.75,.25,1)';
let previousPage;

function animate(el, frames, options = {}) {
  if (reducedMotion.matches || !el?.animate) return null;
  const animation = el.animate(frames, {duration: 220, easing: ease, fill: 'both', ...options});
  running.add(animation);
  const cleanup = () => { running.delete(animation); animation.cancel(); };
  animation.finished.then(cleanup, () => running.delete(animation));
  return animation;
}

reducedMotion.addEventListener('change', event => {
  if (event.matches) for (const animation of running) animation.cancel();
});

export function animatePage(main, pageKey) {
  if (pageKey === previousPage) return;
  previousPage = pageKey;
  for (const animation of pageAnimations) animation.cancel();
  pageAnimations.clear();
  for (const [index, child] of [...main.children].entries()) {
    const animation = animate(child, [
      {opacity: 0, transform: 'translateY(9px)'},
      {opacity: 1, transform: 'translateY(0)'}
    ], {duration: 260, delay: Math.min(index, 4) * 32});
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
    ], {duration: 550, delay: 90});
    if (animation) pageAnimations.add(animation);
  }
}

export function showDialog(dialog) {
  closeLanguageMenus();
  const pending = closingDialogs.get(dialog);
  if (pending) { closingDialogs.delete(dialog); pending.cancel(); }
  delete dialog.dataset.closing;
  if (!dialog.open) dialog.showModal();
  animate(dialog, [
    {opacity: 0, transform: 'translateY(14px) scale(.98)'},
    {opacity: 1, transform: 'translateY(0) scale(1)'}
  ], {duration: 230});
}

export async function closeDialog(dialog) {
  if (!dialog.open || closingDialogs.has(dialog)) return;
  // Cancel an unfinished entrance animation before animating the exit.
  for (const animation of dialog.getAnimations()) animation.cancel();
  const animation = animate(dialog, [
    {opacity: 1, transform: 'translateY(0) scale(1)'},
    {opacity: 0, transform: 'translateY(7px) scale(.99)'}
  ], {duration: 130});
  if (!animation) { dialog.close(); return; }
  dialog.dataset.closing = 'true';
  closingDialogs.set(dialog, animation);
  await animation.finished.catch(() => {});
  if (closingDialogs.get(dialog) !== animation) return;
  closingDialogs.delete(dialog);
  delete dialog.dataset.closing;
  dialog.close();
}

export function animateNotice(el) {
  for (const animation of el.getAnimations()) animation.cancel();
  animate(el, [
    {opacity: 0, transform: 'translate(-50%, 8px) scale(.98)'},
    {opacity: 1, transform: 'translate(-50%, 0) scale(1)'}
  ], {duration: 200});
}

function menuFor(trigger) { return document.getElementById(trigger.getAttribute('aria-controls')); }

function closeMenu(trigger, restoreFocus = false) {
  const menu = menuFor(trigger);
  if (!menu || menu.hidden || trigger.getAttribute('aria-expanded') === 'false') return;
  trigger.setAttribute('aria-expanded', 'false');
  const old = menuAnimations.get(menu);
  old?.cancel();
  const animation = animate(menu, [{opacity: 1}, {opacity: 0, transform: 'translateY(-3px) scale(.99)'}], {duration: 100});
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
  menuAnimations.get(menu)?.cancel();
  menuAnimations.delete(menu);
  menu.hidden = false;
  trigger.setAttribute('aria-expanded', 'true');
  const wrapper = trigger.closest('[data-language-switcher]');
  wrapper.classList.remove('opens-up');
  if (menu.getBoundingClientRect().bottom > innerHeight - 12) wrapper.classList.add('opens-up');
  const animation = animate(menu, [
    {opacity: 0, transform: 'translateY(-5px) scale(.97)'},
    {opacity: 1, transform: 'translateY(0) scale(1)'}
  ], {duration: 170});
  menuAnimations.set(menu, animation);
  const options = [...menu.querySelectorAll('[data-language-option]')];
  const target = focus === 'first' ? options[0] : focus === 'last' ? options.at(-1)
    : options.find(option => option.getAttribute('aria-checked') === 'true');
  target?.focus({preventScroll: true});
}

export function initInteractions({changeLanguage, reportError}) {
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('[data-language-switcher]')) closeLanguageMenus();
    if (event.button !== 0 || reducedMotion.matches) return;
    const target = event.target.closest('.button,.icon-button,.quick-item,.language-trigger,.language-option');
    if (!target || target.disabled) return;
    const bounds = target.getBoundingClientRect();
    const wave = document.createElement('span');
    wave.className = 'tap-wave';
    wave.setAttribute('aria-hidden', 'true');
    const size = Math.max(bounds.width, bounds.height) * 2;
    Object.assign(wave.style, {width: `${size}px`, height: `${size}px`, left: `${event.clientX - bounds.left}px`, top: `${event.clientY - bounds.top}px`});
    target.classList.add('tap-target');
    target.append(wave);
    const animation = animate(wave, [
      {opacity: .13, transform: 'translate(-50%,-50%) scale(0)'},
      {opacity: 0, transform: 'translate(-50%,-50%) scale(1)'}
    ], {duration: 400, easing: 'ease-out'});
    if (animation) animation.finished.then(() => wave.remove(), () => wave.remove()); else wave.remove();
  });

  document.addEventListener('click', async event => {
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
