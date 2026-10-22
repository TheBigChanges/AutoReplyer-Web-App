import {messages} from './translations.js';
import {storage} from './storage.js';

export const languages = {uz: 'O‘zbekcha', ru: 'Русский', en: 'English'};
export function normalizeLanguage(value) {
  const code = String(value || '').toLowerCase().split(/[-_,;]/)[0];
  return Object.hasOwn(languages, code) ? code : null;
}

let language = normalizeLanguage(storage.getItem('ar-language'))
  || normalizeLanguage(window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code)
  || normalizeLanguage(navigator.language) || 'uz';

export const getLanguage = () => language;
export const getLocale = () => ({uz: 'uz-UZ', ru: 'ru-RU', en: 'en-US'}[language]);
export function setLanguage(value, remember = false) {
  const next = normalizeLanguage(value);
  if (!next) return false;
  language = next;
  document.documentElement.lang = next;
  if (remember) storage.setItem('ar-language', next);
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
  const globe = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/></svg>';
  const check = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>';
  return `<div class="language-switcher" data-language-switcher>
    <button type="button" id="${id}" class="language-trigger" data-language-trigger data-current-language="${language}" aria-label="${tr('Tilni tanlash')}: ${languages[language]}" aria-haspopup="menu" aria-expanded="false" aria-controls="${id}-menu">
      ${globe}<span class="language-current">${languages[language]}</span><span class="language-short" aria-hidden="true">${language.toUpperCase()}</span><svg class="language-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
    </button>
    <div id="${id}-menu" class="language-menu" role="menu" aria-label="${tr('Tilni tanlash')}" hidden>
      <div class="language-menu-heading">${globe}<span>${tr('Interfeys tili')}</span></div>
      ${Object.entries(languages).map(([code, name]) => `<button type="button" class="language-option ${code === language ? 'is-selected' : ''}" role="menuitemradio" aria-checked="${code === language}" tabindex="-1" data-language-option="${code}" data-language-owner="${id}" lang="${code}"><span class="language-badge" aria-hidden="true">${code.toUpperCase()}</span><span class="language-name">${name}</span><span class="language-check">${code === language ? check : ''}</span></button>`).join('')}
      <div class="language-menu-note">${tr(storage.persistent ? 'Tanlov shu qurilmada saqlanadi.' : 'Tanlov faqat shu oyna ochiq turguncha saqlanadi.')}</div>
    </div>
  </div>`;
}
