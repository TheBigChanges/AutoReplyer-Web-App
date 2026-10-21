import {messages} from './translations.js';

export const languages = {uz: 'O‘zbekcha', ru: 'Русский', en: 'English'};
export function normalizeLanguage(value) {
  const code = String(value || '').toLowerCase().split(/[-_,;]/)[0];
  return Object.hasOwn(languages, code) ? code : null;
}

let language = normalizeLanguage(localStorage.getItem('ar-language'))
  || normalizeLanguage(window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code)
  || normalizeLanguage(navigator.language) || 'uz';

export const getLanguage = () => language;
export const getLocale = () => ({uz: 'uz-UZ', ru: 'ru-RU', en: 'en-US'}[language]);
export function setLanguage(value, remember = false) {
  const next = normalizeLanguage(value);
  if (!next) return false;
  language = next;
  document.documentElement.lang = next;
  if (remember) localStorage.setItem('ar-language', next);
  return true;
}

export function tr(source, values = {}) {
  return (messages[source]?.[language] ?? source)
    .replace(/\{(\w+)\}/g, (match, key) => values[key] ?? match);
}

export const weekDays = () => ({
  uz: ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'],
  ru: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
  en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
}[language]);

// Only explicitly marked application chrome is translated, never user content.
export function translateChrome() {
  document.documentElement.lang = language;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = tr(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-attr]').forEach(el => {
    for (const attr of el.dataset.i18nAttr.split(' ')) {
      const key = `i18n${attr.replace(/(^|-)([a-z])/g, (_, dash, c) => c.toUpperCase())}`;
      el.dataset[key] ||= el.getAttribute(attr);
      el.setAttribute(attr, tr(el.dataset[key]));
    }
  });
}

export function languageSelector(id) {
  return `<select id="${id}" class="language-select" data-language aria-label="${tr('Tilni tanlash')}">${Object.entries(languages).map(([code, name]) => `<option value="${code}" ${code === language ? 'selected' : ''}>${name}</option>`).join('')}</select>`;
}
