// Mark only entries created during this app visit. A deep link/reload falls
// back to Dashboard instead of sending the user out of the Mini App.
export function createNavigation() {
  const session = `${Date.now()}-${Math.random()}`;
  let position = 0;
  let pending = false;
  const marker = '__autoreplyerNavigation';
  const stateAt = (hash, index) => ({
    ...(history.state && typeof history.state === 'object' ? history.state : {}),
    [marker]: {session, position: index, hash}
  });
  history.replaceState(stateAt(location.hash, 0), '');
  return {
    sync() {
      const entry = history.state?.[marker];
      if (entry?.session === session && entry.hash === location.hash) position = entry.position;
      else history.replaceState(stateAt(location.hash, ++position), '');
      pending = false;
    },
    back() {
      if (pending) return;
      if (position > 0) {
        pending = true;
        history.back();
      } else if (location.hash !== '#dashboard') {
        const oldURL = location.href;
        const target = new URL(oldURL);
        target.hash = 'dashboard';
        history.replaceState(stateAt(target.hash, 0), '', target);
        window.dispatchEvent(new HashChangeEvent('hashchange', {oldURL, newURL: target.href}));
      }
    }
  };
}
