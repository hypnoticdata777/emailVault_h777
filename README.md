# Email Vault POC

Email Vault is a portfolio-quality proof of concept for a Gmail offloader,
inbox cleaner, and portable email export tool.

The product direction is simple: connect to Gmail, save selected emails to
storage the user controls, organize those exports by sender domain or category,
and then optionally clean Gmail according to explicit user rules.

The current codebase proves the safety-first preservation engine behind that
direction: validate a Gmail snapshot, sanitize message content, render and stage
generated artifacts, verify storage checksums, persist an owner-scoped revision,
and only then allow a separate Gmail cleanup/finalization handoff.

This repo can remain private for commercial work while the portfolio story uses
synthetic screenshots, the local web demo, and selected documentation. It uses
synthetic data by default and does not claim to be a production Gmail backup
product.

## Portfolio Snapshot

What this POC proves today:

- A Gmail thread can be modeled as a canonical archive request with stable state
  transitions and controlled API errors.
- Backend preservation can stay separate from Gmail mutation.
- Generated archive artifacts can use server-owned filenames, checksum
  verification, metadata JSON, and manifest JSON.
- Unsafe email HTML can be sanitized before rendering.
- A Gmail Workspace Add-on shell can collect preferences and send signed backend
  requests without mutating Gmail.
- CI can run a stable Python test suite over the core API, state, storage,
  rendering, signing, and add-on boundaries.

What the rescoped product is building toward:

- Preserve Mode: export selected email to local PC, USB, OneDrive-synced folder,
  or another configured target without changing Gmail.
- Clean Inbox Mode: export verified copies first, then label, archive, or mark
  read so Gmail keeps fewer messages in the inbox.
- Free Space Mode: export verified copies first, then move selected Gmail
  messages to a trash/delete queue after explicit opt-in review.
- Domain and category routing so saved email can be organized by sender domain,
  newsletter/source, bank, human sender, automated system, or needs-review state.
- A portable data port for search, knowledge-base, or AI tools without locking
  the user to one downstream product.

What this POC intentionally does not do yet:

- No live Gmail label, mark-read, archive, deletion, or mailbox mutation.
- No whole-mailbox sync or batch cleanup implementation yet.
- No committed Google OAuth client, tokens, real email exports, or secrets.
- No public HTTPS deployment has been selected.
- No cloud storage provider is wired.
- No built-in AI summarization, reply generation, or analysis.
- No legal-grade or byte-perfect backup guarantee is claimed.

Recommended public demo posture:

1. Present this repository as a code and architecture POC.
2. Use the synthetic walkthrough, fixtures, and docs for portfolio review.
3. Validate OAuth, HTTPS hosting, and Gmail mutation privately before any live
   real-data demo.

## Current Status

Done:

- Product scope, requirements, architecture notes, and ADRs.
- Canonical archive contracts, state model, and controlled error categories.
- Synthetic email fixtures and invariant tests.
- FastAPI app with `/health`, `/archive/thread`, and post-completion Gmail
  finalization endpoints.
- Pydantic v2 request/response schemas.
- Google identity verification boundary with synthetic local mode and
  configurable Google ID-token verification mode.
- SQLite revision/audit repository for local P2 persistence tests.
- Safe revision planner for duplicate, new-thread, and updated-thread decisions.
- Local storage provider boundary that stages generated artifacts and verifies
  checksums without marking revisions completed.
- Security and privacy boundaries documented for public-ready development.
- First P3 sanitizer pass for hostile HTML, remote image blocking, and
  plain-text fallback.
- Normalized sanitized message-body output for safe HTML and guaranteed plain
  text.
- Renderer-safe snapshot preparation that keeps raw email HTML out of future PDF
  inputs.
- Expanded sanitizer coverage for table-heavy emails and attachment-adjacent
  unsafe links.
- Artifact manifest planning for future PDF, metadata JSON, and manifest JSON
  outputs with server-generated filenames only.
- PDF renderer boundary ADR covering Playwright/Chromium, blocked network
  requests, disabled JavaScript, and temp workspace cleanup requirements.
- Adapter-based PDF renderer scaffold with tests for sanitized input, blocked
  network policy, disabled JavaScript, PDF bytes, and temp workspace cleanup.
- Playwright/Chromium PDF adapter boundary with tests for JavaScript-disabled
  context creation, route abort handling, PDF options, and close calls.
- Opt-in browser-backed renderer smoke test path for local Chromium PDF checks.
- Renderer PDF output can be staged through the storage provider and checksum
  verified without marking revisions completed.
- Archive coordinator can persist a verified storage revision and audit
  `RENDERED`, `STAGED`, and `VERIFIED` without completing or finalizing Gmail.
- Archive coordinator can append `COMPLETED` only after the verified storage
  audit boundary, still without enabling Gmail finalization.
- Gmail finalization instructions can be requested only after `COMPLETED`, and
  callback results can be recorded only after finalization is pending.
- API routes now expose that finalization boundary through
  `/archive/thread/gmail-finalization` and
  `/archive/thread/gmail-finalization/callback`.
- Archive coordinator that validates, fingerprints, checks duplicates, and keeps
  Gmail finalization disabled on the archive route so Gmail follow-up remains a
  separate explicit handoff.
- Archive route can run the backend preservation path for generated PDFs:
  sanitize, render, stage storage, verify checksums, persist the revision, append
  `COMPLETED`, and still leave Gmail finalization disabled.
- Archive route now stores generated PDF, metadata JSON, and manifest JSON
  artifacts together.
- Trusted permitted attachment copy support exists behind an injectable content
  provider. Signed add-on requests can now supply Gmail attachment bytes as
  base64 with SHA-256, while default local API calls remain descriptor-only.
- GitHub Actions CI runs the stable Python 3.12 test suite with API/test
  dependencies on push and pull request.
- Production identity blocker reduced to configuration and real Google OAuth
  project validation, with unit tests covering the verifier boundary.
- Gmail Workspace Add-on shell with homepage/contextual cards, current-message
  preview behavior, preference capture, configured signed backend archive calls,
  and tests proving it does not mutate Gmail.
- Add-on finalization request/callback helpers use the same signed request
  boundary while Gmail mutation stays disabled pending the permission review.
- Add-on-to-backend HMAC request signing boundary. The archive route can require
  signed add-on headers when `EMAIL_VAULT_ADDON_SIGNING_SECRET` is set, and the
  Apps Script shell can call `/archive/thread` with matching signed headers when
  script properties are configured.
- Docker runtime packaging for the API with non-root execution, `/health`
  healthcheck, persistent `/data` paths, and CI build validation.
- GitHub Actions stable Python CI is passing after the Gmail finalization
  callback category regression fix.
- v0.2 local-first export package contracts for Preserve, Clean Inbox, and Free
  Space modes.
- Sender-domain and category routing with safe folder segments and user
  override support.
- Deterministic classifier rules for newsletter, automated/no-reply,
  bank/financial, human, attachment-heavy, and unknown synthetic mail.
- Dry-run review planning with counts by category, sender domain, export path,
  and planned Gmail action.
- Local export package writer for raw `.eml`, metadata JSON, normalized text,
  trusted attachment files, and manifest JSON with checksum verification.
- Preserve Mode coordinator path that writes verified local export packages and
  records completed preservation while Gmail finalization remains disabled.
- Clean Inbox intent records after completed export while Gmail mutation remains
  disabled.
- Local Preserve Mode CLI that accepts a request JSON file, user-selected export
  root, optional trusted attachment byte mappings, and prints package path plus
  verification summary.
- Local Clean Inbox review CLI that previews batch category, sender-domain
  route, export path, planned Gmail action, and review-required flags without
  writing files or mutating Gmail.
- Local Clean Inbox intent CLI that records post-preservation cleanup intent
  for a completed record while still returning `enabled=false` Gmail
  finalization instructions.
- Local batch CLI that preserves several synthetic request files, produces one
  Clean Inbox review summary, and can record intent only for lower-risk
  approvable items while Gmail mutation remains disabled.
- Public-safe Markdown report output for the local batch CLI, so portfolio demos
  can show summary tables without absolute local package paths.
- Canonical `synthetic-demo` CLI shortcut that runs the public-safe newsletter,
  bank/financial, and unknown-mail walkthrough with fewer flags.
- Local read-only web demo at `/demo` with synthetic review queue data,
  summary counts, and the canonical CLI handoff command.
- Local access split with `/login`, demo access, and an HMAC-signed
  owner-only `/admin` console shell for future live Gmail controls.
- Admin-only Gmail OAuth readiness panel and JSON endpoint that show whether
  the private read-only Gmail OAuth setup is configured.

Next:

1. Add private OAuth callback handling and encrypted token storage after the
   read-only Gmail OAuth setup is configured.
2. Wire read-only Gmail import/listing behind `/admin` before any cleanup
   controls.
3. Expand the local web demo from read-only synthetic preview into a small
   workflow surface only if it remains useful after screenshots.
4. Add optional synthetic screenshots for the public portfolio walkthrough.
5. Validate the signed add-on archive/finalization flow against a real HTTPS API
   and Google OAuth client in a private environment.
6. Decide and document the Gmail mutation permission step for label, mark-read,
   archive, delete/trash queue, and callback success behavior.
7. Keep Free Space Mode trash/delete behavior deferred until review, warning,
   and reversibility protections are privately validated.

## Architecture At A Glance

```text
Gmail Add-on shell
  -> signed export/archive request
  -> FastAPI archive route
  -> identity and signature checks
  -> contract validation and duplicate planning
  -> sanitization and renderer-safe snapshot
  -> export package: .eml, attachments, metadata, readable copy, manifest
  -> local storage staging and checksum verification
  -> SQLite revision and audit history
  -> completed backend preservation
  -> optional Gmail cleanup/finalization request/callback boundary
```

The archive route completes backend preservation only. Gmail changes, including
label, archive, mark-read, trash, or delete behavior, stay behind explicit
review and finalization boundaries.

## Thread vs Email

In Gmail, a **thread** is the conversation container. It can include one message
or many messages with the same conversation history.

An **email message** is one individual sent or received item inside that thread.
Email Vault targets one opened Gmail thread because preserving the whole
conversation is safer than preserving only the currently visible message. If a
thread gets a new message later, that should become a new immutable revision of
the same vault thread.

## Quick Start

```powershell
python -m unittest discover -s tests
```

The foundational contract tests use only the Python standard library. To run the
P2 FastAPI skeleton tests and local API, install the optional API/test
dependencies:

```powershell
python -m pip install -e ".[api,test]"
python -m services.api.app.cli init-db
python -m pytest
python -m uvicorn services.api.app.main:app --reload
```

Open the read-only synthetic local web demo:

```text
http://127.0.0.1:8000/demo
```

Open the local access page:

```text
http://127.0.0.1:8000/login
```

Demo access redirects to the same synthetic read-only demo. Admin access is
disabled until local-only owner credentials are configured:

```powershell
$env:EMAIL_VAULT_WEB_SESSION_SECRET = "replace-with-a-long-local-random-secret"
$env:EMAIL_VAULT_ADMIN_PASSWORD = "replace-with-your-local-admin-password"
python -m uvicorn services.api.app.main:app --reload
```

Then open `http://127.0.0.1:8000/login` and use the admin password to reach
`/admin`. The admin page is a private owner console shell today; it does not
connect Gmail or mutate Gmail yet.

To prepare the private read-only Gmail OAuth step, configure these outside Git:

```powershell
$env:GOOGLE_OAUTH_CLIENT_ID = "your-google-oauth-client-id"
$env:GOOGLE_OAUTH_CLIENT_SECRET = "your-google-oauth-client-secret"
$env:EMAIL_VAULT_OAUTH_REDIRECT_URI = "http://127.0.0.1:8000/oauth/google/callback"
$env:EMAIL_VAULT_GMAIL_OAUTH_SCOPES = "https://www.googleapis.com/auth/gmail.readonly"
```

The admin console and `/admin/gmail/oauth/readiness` will report whether those
private values are ready. Token exchange and real Gmail reading are still the
next private implementation steps.

Run the local Preserve Mode CLI against a synthetic no-attachment fixture:

```powershell
python -m services.api.app.cli preserve-local --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --json
```

The command writes a verified package under the selected export root and prints
the record id, package path, artifact count, byte total, and Gmail finalization
status. It does not mutate Gmail.

Preview Clean Inbox Mode against synthetic fixtures:

```powershell
python -m services.api.app.cli clean-inbox-review --request tests/fixtures/emails/newsletter_digest.json --request tests/fixtures/emails/bank_notice.json --request tests/fixtures/emails/unknown_message.json --mark-read --json
```

The review command reports category, sender domain, planned export path,
planned Gmail action, and whether each item needs review. It does not write
files and does not mutate Gmail.

After a thread has already been preserved, record Clean Inbox intent locally:

```powershell
python -m services.api.app.cli record-clean-inbox-intent --record-id <record-id-from-preserve-local> --mark-read --json
```

This appends the intent audit marker for the completed record while Gmail
finalization remains disabled.

Run the canonical local synthetic demo:

```powershell
python -m services.api.app.cli synthetic-demo --export-root .local/EmailVault --report-markdown .local/demo-report.md --json
```

This shortcut preserves the standard public-safe newsletter, bank/financial, and
unknown synthetic fixtures; prints one Clean Inbox review summary; records
intent only for the lower-risk newsletter item; and writes the public-safe
Markdown report. It does not mutate Gmail.

Run a custom local synthetic batch workflow:

```powershell
python -m services.api.app.cli local-batch --request tests/fixtures/emails/newsletter_digest.json --request tests/fixtures/emails/bank_notice.json --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --mark-read --record-approvable-intents --report-markdown .local/demo-report.md --json
```

This writes verified Preserve Mode packages, prints one Clean Inbox review
summary, and records intent only for lower-risk approvable items. Review-required
items, such as bank/financial or unknown mail, are preserved but not
intent-recorded by default. The Markdown report omits absolute local package
paths and is intended for public-safe synthetic demo review.

To prepare local PDF rendering, install the renderer optional dependency and
Chromium browser runtime:

```powershell
python -m pip install -e ".[renderer]"
python -m playwright install chromium
```

Run the opt-in browser-backed renderer smoke test after installing Chromium:

```powershell
$env:EMAIL_VAULT_RUN_RENDERER_SMOKE = "1"
python -m unittest tests.test_playwright_renderer_smoke
Remove-Item Env:\EMAIL_VAULT_RUN_RENDERER_SMOKE
```

The archive route can preserve generated PDF, metadata JSON, manifest JSON, and
trusted permitted attachment-copy artifacts when the required providers are
installed. If `EMAIL_VAULT_ADDON_SIGNING_SECRET` is set, archive and Gmail
finalization requests must also include matching add-on signature headers. The
add-on can send signed archive requests with trusted attachment bytes and signed
finalization requests when `EMAIL_VAULT_BACKEND_URL` and
`EMAIL_VAULT_ADDON_SIGNING_SECRET` script properties are configured. The route
still does not label Gmail, mark Gmail read, or archive Gmail messages.

Key docs:

- `docs/development.md`
- `docs/api.md`
- `docs/addon.md`
- `docs/deployment.md`
- `docs/data-model.md`
- `docs/security-and-privacy.md`
- `docs/synthetic-walkthrough.md`
- `docs/public-poc-readiness.md`
- `docs/v0.2-local-first-roadmap.md`
- `docs/v0.2-closeout-and-next-wave.md`
- `docs/build-log.md`
- `docs/open-questions.md`
- `docs/current-state-audit.md`
