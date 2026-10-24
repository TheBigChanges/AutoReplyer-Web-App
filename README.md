# AutoReplyer-Web-App

[![CI](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/workflows/ci.yml/badge.svg)](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/workflows/ci.yml)
[![Verify Render](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/workflows/verify-render.yml/badge.svg)](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/workflows/verify-render.yml)

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
node tests/test_api_client.mjs
```

Browser checks require Playwright and installed Google Chrome. Start a static
server for `dist/`, then run `tests/browser_check.py` and `tests/browser_i18n.py`.
Set `AR_BASE_URL` if using a port other than 8765.

The language picker supports mouse, touch and keyboard navigation, Escape and
outside dismissal. `dist/interactions.js` adds brief page entrances, chart
reveals, press feedback, modal transitions and save indicators. Animations honor
the device's reduced-motion preference. Run `tests/browser_interactions.py` to
check focus, rapid navigation, menu bounds, save feedback and reduced motion.

Motion timings and easing are shared CSS tokens in `dist/styles.css`. Entrances
settle gently, presses respond quickly, and interrupted menus/dialogs resume from
the visible frame. The mobile indicator moves using transforms; blur stays
constant. Temporary compositor hints are released when effects finish.
`tests/browser_motion.py` checks reversals, rapid tab changes, cleanup and changing
the reduced-motion setting while animations are running.

Security and regression audit: [AUDIT.md](AUDIT.md). Run
`tests/browser_audit.py` against the FastAPI server to check drafts, request races,
escaped content and credential routing with the production CSP enabled.
`tests/browser_followup.py` checks pending controls across navigation/language
changes, storage-denied/quota fallback and the theme icon. When browser storage
is unavailable, the app keeps working and identifies choices as window-only.

The header Back arrow returns to the previous section in the current app visit.
Direct links and reloaded sections fall back to Dashboard; Dashboard hides the
arrow. `tests/browser_navigation.py` covers native Back/Forward, deep links,
keyboard activation, translated labels and responsive glass styling.

API trust policy is deployment-owned in `dist/config.json`. The default
`{"apiOrigins": []}` allows the same-origin API. If the API is hosted separately,
add its exact HTTPS origin (for example `https://api.example.com`) before deploying
the frontend and restarting the service. Keep `WEBAPP_ORIGINS` on the API set to
the frontend's exact HTTPS origin. A URL typed into Settings or saved by an older
version cannot add a trusted origin. Clear an obsolete Settings API address to
use the same-origin service. API redirects are rejected rather than forwarding
Telegram's signed session to another destination.


The premium visual system is in `dist/premium.css`, loaded after the base styles.
Warm porcelain surfaces, an evergreen sidebar, champagne accents and a decorative
brand orbit carry through dashboard, forms, lists, plans and dialogs. Both themes
share responsive spacing and typography. Theme changes also update Telegram's
header/background and the browser theme color. Pricing and plan permissions are
unchanged. No build step or new dependency is required.

`tests/browser_design.py` checks all 12 sections in three languages, two themes
and four widths, including control bounds, core text contrast, dialog bounds and
native chrome colors. It writes local review screenshots to ignored `artifacts/`.


Entry switches use `POST /api/{kind}/{id}/toggle` with an explicit JSON body such
as `{"is_enabled": false}`. Values must be booleans; empty or ambiguous requests
are rejected. This makes repeat requests safe across stale tabs and retries.
Reopen already-running tabs after upgrading from the old implicit-toggle API.
The reply test previews saved FAQ / standard answers only; it does not run AI,
sleep or scheduler logic or send messages.

The runner explicitly uses one Uvicorn worker. Rate and membership caches are
per process, **not global across multiple instances**. Use a shared limiter
(such as Redis) before horizontally scaling the Render service.

To verify the exact bot version pinned in Dockerfile against real PostgreSQL:

```sh
AUTOREPLYER_SOURCE=/path/to/the/exact/pinned/bot/source \
AR_TEST_DATABASE_URL=postgresql://testuser@127.0.0.1:55479/ar_webapp_test \
python tests/integration_upstream.py
```

Use a disposable local database: the harness rejects non-loopback hosts and
names outside `ar_webapp_test*`. It creates/drops its own random schema, uses
synthetic Telegram sessions and never starts the bot. It verifies source hashes
in `docs/upstream-integration.json` against Docker's pin. Update that manifest
and rerun the integration suite when changing the bot pin. Run
`tests/browser_entry_state.py` against the Web App for stale-tab request payloads
and the localized preview explanation, alongside the existing browser suites.


Continuous checks run in [GitHub Actions](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions)
on every push and pull request (`.github/workflows/ci.yml`): Python3.13/3.14
API/auth/security tests, Node22 syntax/catalog/API-client tests, and the real
PostgreSQL18 contract suite against the exact Docker-pinned bot source. Actions
are pinned to full official release commit SHAs and jobs have read-only repository access.
No production token or database credential is required.

After successful CI for a main-branch push, the separate **Verify Render**
workflow checks that `/api/health` reports that exact commit, the12 public assets
match the tested checkout, unsigned API access returns401, and private paths and
security/cache headers remain protected. It only sends public GET requests and
uploads a JSON report as a seven-day Actions artifact. Keeping this separate
avoids making CI depend on a deploy that might itself wait for passing CI.
You can also run it with **Run workflow** on main or locally:

```sh
python scripts/verify_deploy.py --revision FULL_GITHUB_COMMIT_SHA
```

Health reads Render's `RENDER_GIT_COMMIT` (public commit SHA only); non-Render
local runs report revision=null unless that environment variable is provided.
A healthy older build cannot pass the exact-revision verification. This public
smoke test is separate from real Telegram identity, bot delivery or shared DB
behavior, and the report states its scope.
