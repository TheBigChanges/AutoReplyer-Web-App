# Web App audit — 2026-10-22

Reviewed baseline: `47f2afabae8b42ac2da62ea03bc935b36dac18c6`.
Scope: this Web App's browser code, FastAPI adapter, validation, authentication,
owner isolation, subscription enforcement, deployment settings and dependencies.
The separate bot repository was read only. The initial audit used upstream
`0e62bc3db51498afa308c1905356ec96eb034aba`. Historical source snapshots are in [the audit manifest](docs/upstream-integration.json).
`Dockerfile` selects the active pin; CI prepares and tests that exact source on
every run. See the integration and CI pin-update follow-ups below.

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


## CI and production evidence follow-up — 2026-10-24

The review baseline was9fe010c63134845a7f5bc68190b385ac1adf0b2a. Its repository
tree had no .github/workflows entries and GitHub Actions reported zero runs.

- `.github/workflows/ci.yml` now runs on push, pull_request and manual dispatch.
  Python3.13 (Docker's runtime) and3.14 run the API/auth/security and deployment
  probe tests. Node22 checks all browser-module syntax,350 translations and API
  client URL/redirect behavior. A separate PostgreSQL18 service job downloads
  the exact Docker ref, validates the source manifest and runs the real SQL
  integration suite. No production credentials or bot polling are used.
- Workflow actions are pinned by full commit SHA; jobs use contents:read,
  bounded runtimes and cancellation of superseded runs. At that initial stage browser suites were local-only; the follow-up below
  adds them to CI.
- A separate Verify Render workflow runs after successful main push CI or by
  manual dispatch on main. Pull-request workflow runs do not invoke it. It
  checks the upstream workflow's exact head SHA, uses public GET only, waits
  for deployment, checks the12 asset bodies against the checkout and retains
  a JSON evidence artifact for7 days. It is separate from CI to avoid a
  CI/deploy dependency cycle.
- `/api/health` now reports only a valid40-character public commit from Render's
  RENDER_GIT_COMMIT variable, or null outside that environment. It does not
  load bot modules or access the database. Script regressions prove that a
  healthy older revision, a stale asset, unsigned API access accidentally
  allowed, or missing CSP cannot pass the deployment check.
- Runtime deployment-variable source: [Render default environment variables](https://render.com/docs/environment-variables#all-runtimes).

Evidence boundaries:

- Local Python API/auth/security/deployment probe suite:48 tests passed; both
  JavaScript suites passed. Actual workflow-run results must be read from
  Actions, not inferred from local results or workflow YAML alone.
- On2026-10-24, the user opted into testing through a real Telegram Mini App
  session on a separate test account. The requested flow covered account/plan,
  permitted FAQ/Knowledge edits, schedule synchronization (allowing the60-second
  cache), working with bot + Web App, and a reply to another Telegram account.
  The user replied **"ha ishladi"**. This is user-reported production acceptance,
  not an independently captured session trace or a per-plan/per-feature report.
- Automated isolated PostgreSQL tests cover permissions, owners, limits and
  concurrent writes. They do not run a real Telegram polling bot. Long-running
  bot/Web App interactions, every production plan and rare delivery/cache races
  are not claimed exhaustively verified by that brief user confirmation.
- Rate and membership caches remain process-local. The existing single worker
  remains explicit; multi-instance deployment still needs a shared limiter.
  This remains a documented scaling limitation, not a current Redis deployment.


Observed first automatic runs for commit
`c777c34946bb53737de858505049de436a4f1d6e` on2026-10-24:

- [CI run40072524605](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/runs/40072524605)
  completed successfully: all four jobs passed (48 Python tests on both3.13 and
  3.14, JavaScript checks, and9 pinned-upstream PostgreSQL integration tests).
- [Verify Render run40072572294](https://github.com/TheBigChanges/AutoReplyer-Web-App/actions/runs/40072572294)
  was triggered automatically by that successful CI and passed. Its public
  revision matched the tested commit; all12 assets, unsigned401, private404 and
  required headers passed. The JSON artifact was uploaded with7-day retention.
- These are observed completed GitHub runs, not projected results. Later runs
  remain visible through the README badges and workflow pages. Exact-revision
  public smoke verification does not claim authenticated bot/DB coverage beyond
  the separately recorded isolated tests and user-reported acceptance above.


## Browser CI and remaining coverage — 2026-10-24

The initial review baseline was `de363785ae5b0ca835e96ca7b96a7686b4b137e3`.
During this work the user updated Docker to bot27db864e in Web App commit
`457645789759fe819db5df3ea233db5851b677c4`. That pin is preserved; the source
manifest now binds its exact hashes and retains the old observations under
previous_validation. Upstream changed bot.py and its tests; the imported
db/logic/analytics/i18n files are byte-identical to the prior pin. The current
contract is rechecked by CI rather than treating old-pin results as a new run.
The review correctly noted that browser checks were local-only. A dedicated **Browser / Chromium** CI job
now runs every existing browser suite on push/PR/manual CI: browser_check,
browser_i18n, browser_interactions, browser_audit, browser_followup,
browser_navigation, browser_motion, browser_entry_state and browser_design.

- Playwright1.64.1 is pinned as a test-only dependency, with its matching
  installed Chromium and Linux dependencies. Ubuntu24.04 / Python3.13 job uses
  the same pinned official Actions as the other jobs.
- A shared harness owns the local FastAPI process and test port, excludes
  production credentials, waits for readiness, sets the executable path,
  bounds each suite, collects all results and shuts the server down. Each
  test still supports local Google Chrome through AR_BROWSER_EXECUTABLE.
- Logs, summary JSON and screenshots are uploaded with7-day retention even
  when tests fail. A failed suite fails the job; successful checks from some
  suites do not mask another suite's failure. The downstream Render verifier
  still requires successful overall CI, now including these browser checks.
- No production application behavior, bot repository, plan rules or runtime
  requirements are changed by this browser-test addition.

Coverage remains environment-specific:

| Area | Evidence and boundary |
| --- | --- |
| Free/Plus/Pro/Ultra permissions and expiry | Automated API + real isolated PostgreSQL tests; not every real Telegram production plan independently exercised. |
| Concurrent desired state, owner limits and midnight schedules | Real SQL integration concurrency plus mocked browser stale-tab/request-race tests; not a production traffic soak. |
| Languages, controls and layout | Automated browser suites including UZ/RU/EN,4 widths,2 themes and288 route/layout combinations. |
| Actual Telegram Mini App and bot reply | Prior user-reported test-account success; no independent full session capture or per-feature/per-plan trace. |
| Sustained production behavior | Multi-day operation, multiple Render instances and rare bot/cache/delivery races are not independently certified by these checks. |
| Rate and membership caches | Still in Python process memory, one worker explicit. Shared rate limiting is required before multi-instance scaling; Redis is not deployed. |

The non-urgent scaling limitation is retained explicitly. No real production
load test or authenticated database mutation is performed by CI. A green browser
job means those named isolated browser regressions passed, not that all possible
production behaviors have been proven safe.


## CI pin-update failure fixed — 2026-10-24

Failed run40105913446 on Web App004d850154d9d93f6f94223a5182ca4d066cbe7e
updated the Docker bot pin to1098ee069572fc3488aeca71ae1d1dd83520355d.
Python3.13/3.14, JavaScript and Browser jobs passed. The PostgreSQL job ran zero
tests: its setup required the repository's older27db864e audit manifest to match
Docker before running any SQL. Verify Render was consequently skipped.

The old manual manifest-update requirement is replaced in CI:

- `scripts/prepare_upstream.py` reads the full40-hex Docker ref and downloads that
  immutable upstream archive over HTTPS. It checks the commit-specific archive
  root, extracts through Python's data filter into a fresh directory, requires
  all four imported modules, and records their SHA256 plus archive identity.
- It exports AUTOREPLYER_SOURCE and AR_TEST_UPSTREAM_MANIFEST to subsequent CI
  steps. The integration harness still rejects a different pin, incomplete
  manifests or files changed after preparation, before database initialization.
  No contract test is skipped or converted to a cached success.
- Every run then executes all nine real PostgreSQL contract tests. The prepared
  manifest is source evidence only; only the job outcome proves those tests
  passed. It is uploaded as an upstream-contract artifact with7-day retention.
- The repository JSON remains dated historical evidence. It is no longer a
  prerequisite manual edit for each Docker pin update in CI. Local runs can
  prepare their own manifest; the strict baseline fallback remains available.
- Regression tests cover changed pins, fresh extraction, wrong archives, missing
  modules, unpinned refs, path traversal and post-download changes. All existing
  API/auth/plan/owner tests and isolated PostgreSQL tests remain in the pipeline.
- The user's new pin is preserved. Upstream changes include BIO/name-clock
  state/helpers and translations; original bot repository code is unchanged by
  this Web App fix. Production schema migrations are not run by the adapter.


## Automation integration — 2026-10-26

Reviewed the original bot's Automation Engine v1.0 at
`82c37864dca8a174c962b92c3c2c7b3861df7093` and updated only this Web App's
Docker pin and adapter/frontend. The original bot repository is unchanged.
This includes its current paid-plan-only access, 20-rule limit, keyword/prefix
normalization, deterministic priority and enabled-on-confirmation panel behavior.

- Added an Uzbek/Russian/English Automation section, owner-scoped bootstrap data,
  review-before-enable creation, search, explicit pause/resume and confirmed
  deletion. Uses the original validator and atomic advisory-lock insert helper;
  arbitrary condition/action JSON and owner/plan fields cannot be posted.
- Free/unknown/expired plans cannot create, toggle or delete Automation rules or
  request confirmations. Free bootstrap hides retained Automation data. IDs,
  names, keywords, reply lengths and integer priorities are bounded server-side.
- Delete tokens are random 256-bit values, bound to owner and rule, expire after
  120 seconds, replace older confirmations and are consumed under a lock before
  deletion. Foreign-owner, wrong-rule, stale and concurrent replays fail closed.
  DB helpers independently include the verified owner in their SQL predicates.
- If the running bot has not created its new table yet, bootstrap remains usable;
  the Automation section explains the required bot update, and writes return a
  localized 503. No bot polling, production schema initialization or migration
  is invoked by the adapter. CI verifies all five imported source modules.
- New forms/cards use the existing premium themes, glass dialogs and cancellable
  animation system. Fixed an existing CSS issue where author styles overrode
  `hidden` (including empty search notices and hidden review controls). Reduced
  motion now also suppresses `dialog::backdrop` CSS animations. Search survives
  state/language rerenders. Saved owner text is escaped and remains untranslated.
- The established reply-preview remains FAQ/standard-only, and explicitly says
  Automation/AI/sleep/schedules are excluded. No Gemini call or Telegram send was
  added. Bot delivery still follows the upstream runtime's Offline/sleep/schedule,
  cooldown, connection, permissions and manual-owner-activity gates.

Pre-publication checks, all passed:

| Environment | Evidence |
| --- | --- |
| Python3.14 local | 63 unit/API/auth/security/source/deploy tests |
| PostgreSQL18.6, disposable loopback DB | 11 real pinned-source integration tests; all three paid-plan 20-rule boundaries and parallel last-slot inserts, expiry, owner scope, keyword matching and existing nine contracts |
| Local Chrome + isolated FastAPI/CSP | All 10 browser suites; new Automation suite covers review/duplicate save, pending and failed toggles, search, stale async confirmation, Free/schema gates, three locales/four widths, escaped text, glass and reduced motion |
| Node | All browser module syntax, 384-message catalog and API trust/credential-redirect tests |
| actionlint1.7.12 | Official checksum verified; both workflows clean |
| pip-audit2.10.1 | 18 currently resolved runtime dependencies, no known vulnerabilities; refreshed docs/dependency-audit.json |

Tests used synthetic identities and a throwaway PostgreSQL schema. No production
Telegram account, credentials, DB writes or bot delivery were exercised. This
is not a guarantee that every bug or vulnerability is absent. Docker itself was
not available locally; the existing CI matrix targets Python3.13 and3.14.
Deletion confirmations are process-local, matching the deployment's explicit
single worker. A restart safely invalidates them; multiple instances need a
shared store before scaling. Existing rate/membership cache limits remain.


## Automation v1.1 upstream sync — 2026-10-28

Compared bot82c37864 to65b9a73896ffd86850e04c7ac13e89ab90986c99:
production changes are automation.py, bot.py and i18n.py; db/logic/analytics
remain unchanged. Reviewed all changed production diffs plus README/test changes.
Original bot repo remains read-only. Updated Web App Docker pin to65b9a738.

Server creation limits now match Plus2/Pro10/Ultra30 (administrator effective
Ultra). Optional unique days0–6 and a strict minute time_range require Pro/Ultra.
Use original bot validator for AND/canonical conditions, with bounded flat API
inputs; explicit toggles/owner scope and one-use deletes are preserved. Existing
keyword rules remain compatible. The Web App does not evaluate or send real
messages; original bot runtime enforces day/time, owner timezone, oldest-ID plan
selection (disabled entries count), priority, cooldown, sleep and schedule gates.
UI cards label retained rules excluded by downgrade, and show day/time/timezone.

Added optional day-picker/time fields and review text using existing glass,
control and reduced-motion system, in three languages. Pricing lists2/10/30;
Auto-Reply links to Sleep, matching upstream menu grouping. Existing routes and
explicit Offline updates are preserved. No migrations, new dependencies, polling,
production credentials or production DB writes were introduced.

Local64Python tests passed;12real PostgreSQL18.6 contract tests passed, including
all-plan concurrent last-slot boundaries, strict smart-condition gates and
Monday22:00–Tuesday06:00 boundary/negation behavior. Node syntax,394-message
catalog and API-client credential-routing checks passed. Browser results and
remote CI/deployment proof are recorded in the local session handoff.


## Automation v1.2 parity — 2026-10-30

Reviewed original bot `94e23b19eea02ee6f40d48d85c860feb92b87f86` against
previous pin `65b9a73896ffd86850e04c7ac13e89ab90986c99`: Automation OR matching,
transactional editing, rule/deleted counters and separate analytics kind. Original
bot repository unchanged; only the Web App Docker source pin is updated.

- Create accepts exactly one legacy keyword or a bounded keywords list. Original
  normalization/validation remains authoritative. OR/day/time require Pro/Ultra;
  Plus2/Pro10/Ultra30 quotas remain atomic and Free stays denied.
- Partial PATCH allowlists six content fields and passes the verified owner to
  upstream `update_automation_rule`, which locks the row and merges current data.
  It cannot set enabled state, owner, IDs or counters. Null only removes optional
  day/time filters; Plus may clear retained filters. Legacy punctuation and a
  newer local toggle survive editing. Concurrent separate-field SQL edits merge.
- Authenticated paid-only Statistics exposes owner counts/top names, no reply text
  or chat content. Deleted counts persist through the original atomic delete CTE;
  the real integration suite races a send with deletion and checks exactly one
  increment. The bot itself records delivery; this adapter never sends Telegram
  messages or manufactures real counts. Multi-query reads are best-effort and may
  transiently differ during concurrent updates, as in the bot panel.
- General analytics now includes the distinct Automation category on Pro/Ultra;
  the existing lower-plan payload allowlist remains. Unit and SQL regressions
  check totals without double-counting and deny cross-owner mutation/read leaks.
- Missing v1.2 columns as well as missing tables return localized setup errors;
  bootstrap retains other sections. No production migration is run by the adapter.
- Owner text uses escaping/DOM properties in cards, editor/review and top names.
  New surfaces inherit existing blur, control/dialog motion, both themes and
  reduced preferences. Long names/five maximum-length keywords wrap on mobile;
  invalid stored timezone falls back safely for new counter dates.

Validation:69 local API/auth/security/source/probe tests;15 real PostgreSQL18.6
integration tests against the exact new bot snapshot;412 complete translations
and JS URL/redirect tests. All ten browser suites passed; expanded Automation
regressions additionally cover partial edits, delayed edit vs toggle, retained
filters after downgrade, escaped statistics, stale responses, long owner text and
timezone fallback. Screenshots in ignored artifacts. Dependency audit refreshed
on this date:18 resolved runtime packages, no known vulnerabilities reported.
CI/Render results for the published commit are recorded separately in local
continuity notes. No authenticated production DB writes or real Telegram delivery
were performed; these checks cannot establish the absence of every possible bug.
