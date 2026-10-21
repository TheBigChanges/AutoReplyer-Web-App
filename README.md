# AutoReplyer-Web-App

Web App supports **O‘zbekcha, Русский, and English**. Choose a language in the
top bar or Settings. Your explicit choice is remembered on this device. On first
sign-in, the app uses the language saved in the bot, then the Telegram/device
language, with Uzbek as the fallback. Changing the Web App language does not
change the bot's settings or any user-authored replies, FAQ, or knowledge entries.

UI translations live in `dist/translations.js`; language selection and formatting
are in `dist/i18n.js`. API status and validation messages use the `Accept-Language`
header and `server/i18n.py`. Docker already copies both complete directories.

Checks:

```sh
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_i18n.mjs
```

Browser checks require Playwright and installed Google Chrome. Start a static
server for `dist/`, then run `tests/browser_check.py` and `tests/browser_i18n.py`.
Set `AR_BASE_URL` if using a port other than 8765.
