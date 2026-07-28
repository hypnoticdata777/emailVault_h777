# Build Log

This log records the major implementation steps so the project history remains
easy to follow alongside Git commits.

## 2026-07-27 - v0.2 Export Package Schema

- Added the local-first export package contract for Preserve, Clean Inbox, and
  Free Space modes.
- Planned portable artifacts for raw `.eml`, metadata JSON, manifest JSON,
  normalized text, optional readable HTML/PDF, and attachments.
- Added cleanup gating so Preserve Mode cannot trigger Gmail cleanup.
- Documented export package data model and traceability.
- Validation: `python -m unittest discover -s tests` passed with 124 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Export Route Planning

- Added deterministic sender-domain and category route planning.
- Supported domain-first, category-first, and mixed review-first folder layouts.
- Added sender-domain overrides for user-controlled batching.
- Documented export routing in the data model and traceability.
- Validation: `python -m unittest discover -s tests` passed with 131 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Classifier Seed Fixtures

- Added synthetic fixtures for newsletter, automated/no-reply, bank/financial,
  human, attachments-heavy, and unknown messages.
- Added safe message header support so future classifier rules can inspect
  newsletter and automated-message signals.
- Kept fixtures synthetic with `example.com` addresses and invented content.
- Updated the fixture policy and roadmap status.
- Validation: `python -m unittest discover -s tests` passed with 133 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Deterministic Classifier Rules

- Added transparent local classifier rules for newsletter headers,
  automated/no-reply senders, bank/financial language, human questions,
  attachment-heavy messages, and unknown mail.
- Added classifier evidence so future dry-run review can explain why each
  message was routed into a category.
- Added review-required gating for bank/financial, human, attachment-heavy,
  needs-review, and unknown categories while newsletter and automated mail stay
  eligible for lower-risk cleanup review.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 141 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Dry-Run Review Planning

- Added dry-run review objects that combine classifier results, sender-domain
  routing, export paths, and planned Gmail actions without writing files or
  mutating Gmail.
- Added summary counts by category, sender domain, export path, and planned
  Gmail action so a future review UI can show batch impact before cleanup.
- Kept risky or unknown categories in `needs_review` for Clean Inbox Mode, and
  kept Free Space Mode behind review-only trash queue planning.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 146 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Local Export Package Writer

- Added a local export package writer that writes planned packages under the
  selected export root, sender/category route, and server-owned record folder.
- Generated required portable outputs for raw `.eml`, metadata JSON,
  normalized text, trusted attachment files, and export manifest JSON.
- Added checksum and size verification for every generated file, while keeping
  original attachment filenames as metadata only.
- Rejected missing or mismatched trusted attachment bytes and cleaned partial
  package folders on failure.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 151 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Preserve Mode Export Package Boundary

- Wired Preserve Mode through the local export package writer at the archive
  coordinator layer.
- Reused the existing verified-storage and completed-preservation audit
  boundary so local packages can record `RENDERED`, `STAGED`, `VERIFIED`, and
  `COMPLETED` only after checksum-verified output exists.
- Kept Gmail finalization disabled on Preserve Mode responses.
- Added tests for successful local package preservation, duplicate short-circuit
  behavior, and missing attachment-byte rejection without archive state writes.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 154 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Clean Inbox Intent Records

- Added `CLEAN_INBOX_INTENT_RECORDED` as a post-completion archive state.
- Added an archive coordinator method that records Clean Inbox intent after a
  completed archive while returning Gmail cleanup instructions with
  `enabled=false`.
- Preserved the explicit Gmail finalization boundary: live label/archive/mark
  read instructions still require the separate finalization request path.
- Added tests for completed-only intent recording, disabled mutation
  instructions, pre-completion rejection, and later explicit finalization.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Closeout And Public POC Readiness Sweep

- Added a v0.2 closeout and next-wave document that records what the
  local-first implementation now proves.
- Updated README and implementation plan so they no longer describe v0.2
  foundation work as future work.
- Refreshed public POC readiness notes with the completed v0.2 foundation and
  the next recommended blockers.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - Synthetic Walkthrough For Public Review

- Added a public-safe synthetic walkthrough for portfolio, investor, and
  non-engineer review.
- Documented the demo story from Gmail batch preview through classification,
  dry-run review, verified local export package, and Clean Inbox intent.
- Added a screenshot checklist and short public demo script that avoid real
  Gmail data and live mutation claims.
- Updated README, public POC readiness, closeout, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - Local Preserve Mode CLI

- Added `python -m services.api.app.cli preserve-local` as the first hands-on
  local Preserve Mode interface.
- The command accepts an archive request JSON file, selected export root,
  optional trusted attachment byte mappings, and folder layout controls.
- It reuses the archive coordinator local export package path and prints status,
  record id, package path, verification count, byte total, and Gmail
  finalization status.
- Added CLI tests for database bootstrap, successful local package export,
  duplicate short-circuit behavior, and controlled missing-attachment failures.
- Updated README, development docs, closeout notes, and current-state audit.
- Validation: `python -m unittest discover -s tests` passed with 161 tests and
  17 expected skips.

## 2026-07-27 - Local Clean Inbox Review CLI

- Added `python -m services.api.app.cli clean-inbox-review` so local demos can
  preview Clean Inbox category, sender-domain route, export path, planned Gmail
  action, review-required flag, and classifier evidence for one or more
  synthetic request files.
- Added `python -m services.api.app.cli record-clean-inbox-intent` so completed
  Preserve Mode records can receive a local `CLEAN_INBOX_INTENT_RECORDED` audit
  marker.
- Kept Gmail mutation disabled in both commands. The review command does not
  write files, and the intent command returns Gmail finalization instructions
  with `enabled=false`.
- Added CLI tests for review summaries, sender-domain overrides, intent
  recording after completed preservation, and controlled rejection of unknown
  records.
- Updated README, development docs, closeout notes, and current-state audit.
- Validation: `python -m unittest discover -s tests` passed with 165 tests and
  17 expected skips.

## 2026-07-27 - Local Batch Workflow CLI

- Added `python -m services.api.app.cli local-batch` as the first one-command
  local Preserve-to-review demo path.
- The command preserves each supplied synthetic request to the selected export
  root, generates one Clean Inbox review summary, and can record Clean Inbox
  intent for lower-risk approvable items only.
- Kept bank/financial, human, attachment-heavy, unknown, and other
  review-required categories out of automatic intent recording.
- Kept Gmail mutation disabled. The command writes local export packages and
  audit intent markers only; it does not label, mark read, archive, trash, or
  delete Gmail messages.
- Added CLI tests for batch preservation/review/approvable intent recording and
  review-only batch behavior when intent recording is not requested.
- Updated README, development docs, closeout notes, current-state audit, and
  traceability.
- Validation: `python -m unittest discover -s tests` passed with 167 tests and
  17 expected skips.

## 2026-07-27 - Public-Safe Batch Report Output

- Added `--report-markdown` to `python -m services.api.app.cli local-batch`.
- The report writes a readable Markdown summary with batch counts, planned Gmail
  action counts, per-thread category/route/action rows, preservation status, and
  intent status.
- Omitted absolute local package paths from the report so synthetic portfolio
  demos can be shared without exposing user machine paths.
- Kept JSON output unchanged for automation and tests.
- Added CLI coverage for report generation and path omission.
- Updated README, development docs, synthetic walkthrough, current-state audit,
  public readiness, closeout notes, implementation plan, and traceability.
- Validation: `python -m unittest discover -s tests` passed with 168 tests and
  17 expected skips.

## 2026-07-27 - Canonical Synthetic Demo CLI

- Added `python -m services.api.app.cli synthetic-demo` as a short public-safe
  command for the canonical newsletter, bank/financial, and unknown fixture
  walkthrough.
- Reused the local batch workflow so the shortcut preserves verified packages,
  produces Clean Inbox review output, records intent only for the lower-risk
  newsletter item, and can write the public-safe Markdown report.
- Added a rerun guard so an already-recorded Clean Inbox intent does not make a
  repeated local demo fail.
- Added CLI tests for the short demo command and repeated demo execution.
- Updated README, development docs, synthetic walkthrough, current-state audit,
  public readiness, closeout notes, implementation plan, and traceability.
- Validation: `python -m unittest discover -s tests` passed with 170 tests and
  17 expected skips.

## 2026-07-27 - Read-Only Local Web Demo

- Added `GET /demo` as the first local web UI surface for the public-safe
  synthetic walkthrough.
- Added `GET /demo/data` so the same canonical newsletter, bank/financial, and
  unknown review data can be consumed as JSON by tests or future UI work.
- Kept the web demo read-only: it does not write export packages, append audit
  events, require Gmail credentials, or mutate Gmail.
- Included summary counts, review queue rows, route planning, planned Gmail
  actions, and the canonical `synthetic-demo` CLI handoff command.
- Added API tests for the HTML page and JSON data safety flags.
- Updated README, API docs, development docs, current-state audit, public
  readiness, closeout notes, implementation plan, and traceability.
- Validation: `python -m unittest discover -s tests` passed locally with 172
  tests and 19 skips because API optional dependencies are not installed in this
  local shell. The new FastAPI demo route tests run when `.[api,test]` is
  installed.

## 2026-07-27 - Local Demo/Admin Access Split

- Added `/login` as the local web access page with separate Demo Access and
  Admin Access paths.
- Kept Demo Access synthetic and safe by redirecting to the existing read-only
  `/demo` page.
- Added an owner-only `/admin` console shell protected by an HMAC-signed browser
  session cookie.
- Kept admin login disabled until `EMAIL_VAULT_ADMIN_PASSWORD` and
  `EMAIL_VAULT_WEB_SESSION_SECRET` are configured outside Git.
- Documented that `/admin` is the future private live Gmail control surface, but
  it does not connect Gmail, store OAuth tokens, write files, or mutate Gmail
  yet.
- Fixed the admin page grid so long local command snippets scroll inside their
  panels instead of pushing the page off-center on wide browser windows.

## 2026-07-27 - Admin Gmail OAuth Readiness

- Added private read-only Gmail OAuth readiness settings for client id, client
  secret, redirect URI, and Gmail scopes.
- Added a standard-library OAuth readiness helper that reports missing private
  setup, builds a future authorization URL only when configured, and flags
  mutation-capable Gmail scopes.
- Added an admin-only `/admin/gmail/oauth/readiness` JSON endpoint.
- Updated `/admin` so the owner console shows OAuth readiness, missing setup,
  requested scopes, and whether cleanup/mutation scopes are present.
- Kept the first Gmail OAuth scope read-only and kept token exchange, real Gmail
  reads, file writes, and Gmail mutation out of this step.

## 2026-07-27 - OAuth Callback And Token Storage Readiness

- Added token-storage readiness settings for `EMAIL_VAULT_TOKEN_STORE_PATH` and
  `EMAIL_VAULT_TOKEN_ENCRYPTION_KEY`.
- Added a standard-library token-storage readiness helper that reports missing
  private token-store setup and explicitly keeps plaintext token storage
  disabled.
- Added admin-only `/admin/gmail/token-storage/readiness`.
- Added local `/oauth/google/callback` shell for the future Google OAuth
  authorization-code redirect.
- Kept the callback safe by discarding authorization codes until token exchange
  and encrypted storage are implemented.

## 2026-07-27 - Admin Console Visual Polish

- Updated the owner admin console so it reads more like a working inbox command
  center instead of a plain status page.
- Added a stronger product header, visible Preserve/Clean Inbox/Free Space mode
  cards, and a safety pipeline from read-only connection through preservation,
  review, and locked cleanup.
- Kept the polish honest: Gmail stays locked, token exchange remains pending,
  and no live Gmail read/write behavior was added.
