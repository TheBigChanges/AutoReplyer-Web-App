// Deployment-owned allowlist. A saved form value must never choose who receives
// Telegram's signed session. Relative/same-origin APIs need no configuration.
let policy;
async function apiOrigins() {
  policy ||= (async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(new URL('./config.json', import.meta.url), {redirect: 'error', credentials: 'omit', cache: 'no-cache', signal: controller.signal});
      if (!response.ok) throw Error('API policy unavailable');
      const config = await response.json();
      if (!Array.isArray(config.apiOrigins)) throw Error('Invalid API policy');
      return config.apiOrigins;
    } finally { clearTimeout(timer); }
  })().catch(error => { policy = undefined; throw error; });
  return policy;
}

export function normalizeApiBase(value, origins, current = location.href) {
  const text = String(value || '').trim();
  if (!text) return '';
  const here = new URL(current);
  const url = new URL(text);
  const localDevelopment = ['localhost', '127.0.0.1', '[::1]'].includes(here.hostname)
    && url.origin === here.origin && url.protocol === 'http:';
  if ((url.protocol !== 'https:' && !localDevelopment) || url.username || url.password || url.search || url.hash) throw Error('Untrusted API address');
  if (url.origin !== here.origin && !origins.includes(url.origin)) throw Error('Untrusted API address');
  return url.href.replace(/\/+$/, '');
}

export async function trustedApiBase(value) {
  // Same-origin does not depend on an external policy request succeeding.
  if (!String(value || '').trim()) return '';
  return normalizeApiBase(value, await apiOrigins());
}

export async function requestJSON(base, path, {method = 'GET', body, initData = '', language = 'uz'} = {}) {
  base = await trustedApiBase(base);
  if (!/^\/api\/[a-z0-9/?=&-]+$/i.test(path)) throw Error('Invalid API path');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${base}${path}`, {
      method, redirect: 'error', credentials: 'omit', referrerPolicy: 'no-referrer',
      cache: 'no-store', signal: controller.signal,
      headers: {'Content-Type': 'application/json', 'X-Telegram-Init-Data': initData, 'Accept-Language': language},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})
    });
    const data = await response.json();
    if (!response.ok) {
      const error = Error(typeof data.detail === 'string' ? data.detail : 'API request failed');
      error.status = response.status;
      throw error;
    }
    return data;
  } finally { clearTimeout(timer); }
}
