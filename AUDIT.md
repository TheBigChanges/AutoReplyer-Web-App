# Web App audit — 2026-10-22

Reviewed baseline: `47f2afabae8b42ac2da62ea03bc935b36dac18c6`.
Scope: this Web App's browser code, FastAPI adapter, validation, authentication,
owner isolation, subscription enforcement, deployment settings and dependencies.
The separate bot repository was read only. The initial audit used upstream
`0e62bc3db51498afa308c1905356ec96eb034aba`. The current Docker pin is
`eb8a14f87b4f2faf357962b068a0cb040efed76c`; see the 2026-10-23 integration
follow-up below and [the source manifest](docs/upstream-integration.json).

## Findings and fixes

| Finding | Impact | Fix and evidence |
| --- | --- | --- |
| A Settings/localStorage API URL could receive signed Telegram initData; fetch also followed redirects. | High, conditional on an untrusted configured address or API redirect. A valid stolen session can authorize requests until expiry. | `dist/api-client.js` accepts same-origin or deployment-approved HTTPS origins in `dist/config.json`, rejects credentials/query/fragment/unsafe protocols, omits cookies and rejects redirects. Real loopback redirect regression confirms no request reaches the redirect target. Browser regression confirms an untrusted saved address receives no request. |
| API bodies were parsed without a size or read deadline. | Medium, resource exhaustion before authentication. | ASGI boundary caps actual streamed bytes at 64 KiB, checks declared length, imposes a total 10-second body deadline and handles malformed/deep JSON. Oversized unsigned, chunked-without-length and slow-body tests exercise rejection before application work. |
| Paid analytics details were hidden by the UI but returned by the API. In particular, `kinds.skipped` bypassed the top-level Ultra-only `skipped` field. | Medium, subscription restriction bypass. | API now allowlists only AI count on Free/Plus, the four distribution categories on Pro/Ultra, and skipped count only on Ultra. Plan-matrix tests check payloads, including unknown plans falling back to Free. |
| Preview matched every enabled FAQ after a downgrade, while the bot uses only the first entries within the current plan limit. | Low, incorrect preview. | `/api/test` applies 15/30/65 entry limits before the upstream matcher. Regression checks a Plus owner with 30 existing entries. |
| Switching a setting rebuilt forms and discarded unsaved text. | Medium, user data loss. | Same-route renders restore form values, radio/checkbox choices, selection and preview. Pending forms retain their original nodes and busy state. Browser regression verifies toggling and language changes during a held save. |
| Delayed analytics/preview responses could overwrite newer UI; repeat form submissions could duplicate work. | Medium, incorrect state or duplicate writes. | Analytics uses request generations, preview results update only their original connected form, stale saves/deletes cannot close replacement dialogs, pending submits/deletes are guarded. Held-response browser tests verify latest analytics, new preview draft and single save. |
| During authentication, hash navigation could render demo controls while the session was still loading. | Low, misleading UI. | Loading routes display verification content and mutations require explicit Demo or Live mode. Analytics failure after successful bootstrap no longer resets a valid authenticated account to connection failure. |
| Invalid stored timezone, unknown plan, out-of-range item IDs and boolean cooldown values were insufficiently handled. | Low, errors/ambiguous validation. | Timezone fallback, Free fallback, bounded positive serial IDs and strict numeric cooldown. API regressions exercise these boundaries. |
| Missing CSP and deployment-policy validation left avoidable browser attack surface. | Hardening. | CSP limits scripts to this service and Telegram SDK, blocks objects/base changes and permits official Telegram framing. Explicit origin validation, API no-store, static revalidation, no-referrer, nosniff and restricted device permissions. Tests verify headers and private-file paths. |

## Verified boundaries

- Telegram HMAC validation, one-hour age limit, duplicate query key rejection,
  signed positive integer identity and wrong-token/tampering rejection remain.
  Reviewed against [Telegram's validation specification](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).
- API identity is obtained from the verified session, never request owner IDs.
  Tests cover a real signed request, blocked user, required-channel denial/cache,
  the per-user rate limit and unsigned requests.
- Every exposed CRUD operation passes the verified owner into upstream helpers.
  The pinned upstream SQL was reviewed for owner predicates and parameterized
  values. Creation helpers use PostgreSQL advisory transactions to enforce limits.
  Cross-owner missing records return 404. Owners can delete saved data after a
  downgrade. No client can set its plan through Settings.
- Free cannot write paid text/FAQ/AI/knowledge settings; Knowledge create/edit/
  toggle requires Ultra; analytics history is gated server-side. Existing plan
  limits and administrator exemption remain.
- User-written text is escaped or assigned through textContent. Browser checks
  include HTML-like Telegram names and reply drafts. Three languages and existing
  animation/reduced-motion behavior are preserved.
- Fresh requirements installation successfully imports pinned `db`, `logic` and
  `analytics` modules without starting the bot, connecting to PostgreSQL or
  running migrations.

## Validation

- 40 Python unit/API/security tests pass with a fresh requirements environment.
- Node translation checks pass for 346 messages; API-client URL/redirect tests pass.
- Four Chrome suites: `browser_check.py`, `browser_i18n.py`,
  `browser_interactions.py`, `browser_audit.py`. They cover CRUD, all 12 routes,
  three languages, four viewport widths, keyboard/reduced motion and the new
  security/state regressions. The final run uses the FastAPI service and CSP.
- `pip-audit -r requirements.txt` resolved 18 dependencies on this date and
  reported no known vulnerabilities. Snapshot:
  [dependency-audit.json](docs/dependency-audit.json). This is evidence about
  those resolved versions, not the unknown packages inside an older live deploy.

## Deployment and limits

Deploy the complete repository using the existing Dockerfile; it already copies
all of `dist/` and `server/`. Same-origin installs keep `apiOrigins` empty.
Separate APIs must be explicitly listed in `dist/config.json`; Settings alone
cannot approve a new origin. HTTP is supported only for same-origin loopback
development, and credentials are never forwarded through redirects.

This is a source and local runtime audit, with mock-backed API writes. It is not
a certification that all vulnerabilities are absent. No production Telegram
session, database credentials or real account writes were used. The original bot
was not changed. Docker itself was not available locally; runtime checks used
Python 3.14 with freshly resolved requirements (Docker targets Python 3.13).
Rate/membership caches remain process-local; the configured deployment runs one
Uvicorn worker. Live deployment observations are recorded separately below.

## Live observation

Public Render endpoint supplied by the user:
`https://autoreplyer-web-app.onrender.com`. Only unauthenticated read requests
and public browser assets are used for live verification.

Before publishing the fixes, `/` and `/api/health` returned 200, unsigned
`/api/bootstrap` returned 401 with `Cache-Control: no-store`. The served app.js
blob matched the audited baseline (`e12ce155da0f30be1ecad472537794dbdf8fd95e`).
The baseline did not send CSP and exposed `/openapi.json`; `/config.json` was
absent as expected before this change. These observations confirm the service
was reachable and running the source that was reviewed, without touching a real
account or database.

After implementation commit `a0cbc74b381b4dc60a1ae6168be9fa4fbbfc2460`, Render
served `/app.js`, `/api-client.js` and `/config.json` byte-for-byte identical to
the tested files. CSP, no-referrer, nosniff, permissions policy and cache rules
were present. `/api/health` returned 200; unsigned `/api/bootstrap` returned 401;
`/openapi.json` and `/server/auth.py` returned 404. A real Chrome visit to the
public service exercised 12 routes, Uzbek/Russian/English and the 390 px mobile
navigation with no page errors. No authenticated production writes were made.

## Follow-up bug check — 2026-10-22

Four additional UI defects were reproduced against the audited version and fixed:

- Pending switches lost their optimistic checked value and became clickable again
  after language changes or navigating away/back. Operations are now keyed to the
  account and setting/entry; rebuilt controls retain checked/disabled state until
  completion, reject duplicate changes, and roll back correctly on failure.
  A delayed toggle also tolerates an entry being deleted in the meantime.
- A pending settings form was tracked only while its DOM node stayed mounted.
  Returning to that screen could enable a duplicate save and lose the pending
  draft. Pending main forms now survive route changes, scoped by account/form kind;
  unrelated forms remain usable. The original busy form is restored on return.
- Denied localStorage access stopped module initialization and left a blank app;
  quota failures could also interrupt preferences and demo saves. `dist/storage.js`
  catches both failures and retains values in the current window. The UI says
  when changes/choices are session-only rather than claiming device persistence.
- The theme button's static icon marker overwrote its current icon during render,
  and a remembered dark theme still started with the moon icon. The marker now
  tracks the actual theme on startup and after switching, so renders stay correct.

`tests/browser_followup.py` exercises held requests, navigation, retry and failure,
duplicate prevention, authoritative entry toggle results, blocked storage, quota
failure and theme icon persistence. It passes alongside the four existing Chrome
suites with no page errors. Node translation checks now cover 349 messages. The
backend, authentication, tariff rules and original bot code are unchanged by this
follow-up.


## Concurrency and current upstream follow-up — 2026-10-23

Baseline: Web App `b5067c92b311b11059a80fb6b3a1c413f376dd92`, Docker upstream
`eb8a14f87b4f2faf357962b068a0cb040efed76c` (the user's newer pin is preserved).
No original bot repository changes were made.

- **Confirmed scheduler race:** two concurrent requests were held immediately
  after reading the same real PostgreSQL row. Both read enabled=true, both
  returned false and the row ended false after two implicit flips. The old
  read/negate/write happened outside the upstream write transaction.
- **Fix:** entry controls now send their desired `is_enabled` boolean. The API
  requires it and never reads/negates a schedule's old state. It passes explicit
  schedule state to the upstream transaction and FAQ/Knowledge state to the
  new pinned bot's owner-scoped setters. Duplicates and retries set the same value.
  Existing ownership, plan checks, schedule validation and cache invalidation
  remain. Missing/string/numeric booleans are rejected without writes. The
  `/toggle` path is retained, with an explicit-state body; already-open older
  tabs must reload and cannot silently make an ambiguous change.
- **Rate-limit scope:** counters and membership cache are still process-local.
  `server.run` explicitly starts **one worker**, including when a platform sets
  `WEB_CONCURRENCY`. This does not make the limit global across Render instances.
  Horizontal scaling requires a shared limiter such as Redis before enabling
  more instances. Production instance count was not inspected. No Redis service,
  schema migration or new runtime dependency was introduced for this follow-up.
- **Preview scope:** the existing test is intentionally saved FAQ / standard
  reply only. The user explicitly chose clearer wording rather than real AI.
  Title and explanation now identify the scope in Uzbek/Russian/English and
  state that AI, sleep mode and schedules are outside the test. It sends no
  Telegram message and makes no Gemini request or AI-quota/analytics write.

Validation against the exact current upstream source:

- 43 Python API/auth/security tests passed; Node checked all350 messages and
  app.js syntax. New API cases check strict explicit state, repeat requests and
  keeping one worker despite a platform worker environment.
- **9 real PostgreSQL integration tests passed**, using PostgreSQL18.6 in a
  temporary loopback cluster and a random per-run schema. The tests use real
  Telegram HMAC verification with a synthetic token, the real pinned db/logic/
  analytics modules and actual SQL; no DB helpers are mocked. They cover
  bootstrap/connection/language, FAQ and Knowledge CRUD, cross-owner denial,
  Free/Plus/Pro/Ultra permissions and expiry, FAQ15/30/65, Knowledge55,
  schedule1/3/10/30 limits at concurrent last-slot boundaries, scheduler edit,
  midnight conflicts/cache invalidation, four concurrent identical state writes,
  real analytics periods/payload filtering and preview side effects.
- The integration harness permits only a loopback `ar_webapp_test*` database,
  initializes only its random schema and cleans it up. The running Web App
  never calls init_db. Source SHA256 checks and the Docker pin are bound to
  [upstream-integration.json](docs/upstream-integration.json); changing the pin
  makes the contract test fail until the manifest/audit are refreshed.
- No real production Telegram session, Gemini call or database write was used.
  Docker is unavailable locally: runtime tests used Python3.14, while Docker
  targets Python3.13. Historical audit evidence above remains dated separately.

- Six Chrome suites passed with the actual local FastAPI/CSP server and mocked
  authenticated browser APIs: browser_entry_state, browser_followup,
  browser_i18n, browser_interactions, browser_audit and browser_design. New
  regressions cover two stale tabs sending the same off intent for all three
  entry types and the preview explanation in three languages at320px. The
  design matrix still passes288 theme/language/viewport/route combinations.
