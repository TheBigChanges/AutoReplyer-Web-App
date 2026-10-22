// Telegram webviews may deny storage or exhaust its quota. Keep this window
// usable while reporting whether a preference actually survived persistence.
const memory = new Map();
let persistent = true;
export const storage = {
  get persistent() { return persistent; },
  getItem(key) {
    if (memory.has(key)) return memory.get(key);
    try { return globalThis.localStorage.getItem(key); }
    catch { persistent = false; return null; }
  },
  setItem(key, value) {
    value = String(value);
    memory.set(key, value);
    try { globalThis.localStorage.setItem(key, value); return true; }
    catch { persistent = false; return false; }
  }
};
