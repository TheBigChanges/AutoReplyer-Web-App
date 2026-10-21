import assert from 'node:assert/strict';
import {messages} from '../dist/translations.js';

const values = new Map();
globalThis.localStorage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)};
globalThis.window = {Telegram: {WebApp: {initDataUnsafe: {user: {language_code: 'ru-RU'}}}}};
globalThis.document = {documentElement: {}, querySelectorAll: () => []};
const {tr, getLanguage, setLanguage, normalizeLanguage, weekDays} = await import('../dist/i18n.js');

assert.equal(getLanguage(), 'ru');
assert.equal(tr('Sozlamalar'), 'Настройки');
assert.equal(tr('Salom, {0}', {0: 'Alex <user>'}), 'Здравствуйте, Alex <user>');
assert.equal(weekDays()[0], 'Пн');
setLanguage('en', true);
assert.equal(values.get('ar-language'), 'en');
assert.equal(document.documentElement.lang, 'en');
assert.equal(tr('Uyqu rejimi'), 'Sleep mode');
assert.equal(weekDays()[6], 'Sun');
assert.equal(setLanguage('invalid'), false);
assert.equal(getLanguage(), 'en');
assert.equal(normalizeLanguage('uz-UZ'), 'uz');
assert.equal(normalizeLanguage('en-GB'), 'en');
assert.equal(normalizeLanguage('ru-RU,ru;q=0.9'), 'ru');
assert.equal(normalizeLanguage('de'), null);
setLanguage('uz');
assert.equal(tr('Sozlamalar'), 'Sozlamalar');
assert.equal(tr('Custom user text'), 'Custom user text');
const placeholders = text => [...text.matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort();
for (const [key, translations] of Object.entries(messages)) {
  for (const lang of ['uz', 'ru', 'en']) {
    assert.ok(translations[lang]?.trim(), `${lang}: ${key}`);
    assert.deepEqual(placeholders(translations[lang]), placeholders(key), `${lang} placeholders: ${key}`);
  }
}
console.log(`Three complete catalogs checked: ${Object.keys(messages).length} messages, language detection, persistence, placeholders, weekdays.`);
