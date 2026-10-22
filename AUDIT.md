# Web App audit — 2026-10-22

Reviewed baseline: `47f2afabae8b42ac2da62ea03bc935b36dac18c6`.
Scope: this Web App's browser code, FastAPI adapter, validation, authentication,
owner isolation, subscription enforcement, deployment settings and dependencies.
The separate bot repository was read only. Its pinned source remains
`0e62bc3db51498afa308c1905356ec96eb034aba`.

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
