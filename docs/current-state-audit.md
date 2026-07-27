# Current State Audit

## Repository Tree

At the start of this work the repository contained only `.git/` metadata. Git
reported: `No commits yet on main...origin/main [gone]`.

## Current Architecture and Stack

No application architecture, dependency manifest, tests, CI, migrations, Docker
files, README, or source entry points existed before this P0/P1 foundation.

The P1 foundation uses Python standard-library modules so the core contracts and
invariant tests can run immediately without package installation. P2 adds
FastAPI/Pydantic modules behind optional dependencies. Early P3 work adds
dependency-light sanitization, renderer-safe snapshot preparation, artifact
manifest planning, the PDF renderer boundary ADR, an adapter-based renderer
scaffold, and a Playwright/Chromium adapter boundary.

## What Already Works

- Canonical archive request, response, state, and error concepts are represented.
- Synthetic JSON fixtures can be loaded and validated.
- Attachment allowlist and size limits are enforced by contract validation.
- Storage path helper rejects traversal, absolute paths, nested paths, and null
  bytes.
- Redaction helper prevents sensitive fixture values from being emitted into
  structured log extras.
- State transition policy blocks Gmail finalization before completed
  preservation.
- Duplicate fingerprinting is deterministic and changes when a thread gains a
  message.
- FastAPI application factory, `/health`, and `/archive/thread` stub route exist
  when optional API dependencies are installed.
- The archive route requires a bearer identity and keeps Gmail finalization
  disabled while backend preservation runs.
- Identity verification is selectable: synthetic local mode remains the default,
  and Google ID-token verifier mode can validate tokens for a configured OAuth
  client ID.
- SQLite-backed revision persistence stores owner-scoped archive references and
  ordered audit events without storing email content.
- The archive coordinator now uses a safe revision planner for duplicate,
  new-thread, and updated-thread decisions without writing completed records.
- The local storage provider can stage generated artifacts and verify checksums
  without marking revisions completed.
- HTML sanitization removes hostile tags and attributes, blocks remote image
  sources, and provides plain-text fallback output.
- Sanitized message normalization produces safe HTML plus guaranteed plain text
  for future rendering.
- Renderer-safe snapshots keep raw email HTML out of renderer inputs.
- Artifact manifest planning declares future PDF, metadata JSON, and manifest
  JSON outputs with server-generated trusted filenames.
- ADR 0003 records the PDF renderer boundary before renderer implementation.
- The first PDF renderer scaffold builds renderer HTML from sanitized snapshots,
  applies disabled-JavaScript and blocked-network policy, reads generated PDF
  bytes, and cleans temporary workspaces on success and failure.
- The Playwright adapter boundary creates JavaScript-disabled Chromium contexts,
  registers route abortion for network requests, renders PDF output, and closes
  browser resources.
- An opt-in browser-backed renderer smoke test exists for local Chromium PDF
  checks when `EMAIL_VAULT_RUN_RENDERER_SMOKE=1` is set.
- Rendered PDF bytes can be staged through the storage provider and checksum
  verified while temporary source workspaces are cleaned.
- The archive coordinator can create a revision after verified storage and
  append `RENDERED`, `STAGED`, and `VERIFIED` audit events without completing or
  finalizing Gmail.
- The archive coordinator can append `COMPLETED` after verified storage state
  exists, without creating Gmail finalization instructions.
- The archive route can now run the backend preservation path for generated PDF
  output: sanitize, render, stage and verify storage, persist the revision,
  append `COMPLETED`, and return `PRESERVED` while Gmail finalization remains
  disabled.
- Metadata JSON and manifest JSON artifacts are generated and staged with the
  PDF.
- Trusted permitted attachment copy support exists behind an injectable content
  provider. When bytes are supplied, the archive path verifies size/checksum,
  stages the attachment under a server-generated name, and records copied status
  in metadata and manifest JSON.
- Signed add-on archive requests can now supply trusted Gmail attachment bytes
  as base64 plus SHA-256 so the backend provider can verify and copy them.
- Gmail finalization instructions can be requested only after owner-scoped
  `COMPLETED` state, and callback success/failure can be recorded only after
  `GMAIL_FINALIZATION_PENDING`.
- The API exposes the Gmail finalization request and callback boundary at
  `/archive/thread/gmail-finalization` and
  `/archive/thread/gmail-finalization/callback`.
- Local API runs can bootstrap the configured SQLite schema with
  `python -m services.api.app.cli init-db`.
- GitHub Actions CI runs the stable Python 3.12 unit test suite with API/test
  dependencies on push and pull request.
- A Gmail Workspace Add-on shell exists with homepage/contextual cards,
  preference capture, configured signed backend archive calls, and tests that
  guard against Gmail mutation calls.
- The add-on shell can request Gmail finalization instructions and includes a
  signed callback helper, while still avoiding live Gmail mutation calls.
- Add-on-to-backend HMAC request signing exists. The API can enforce signature
  headers when configured, and the Apps Script shell can call the archive route
  with matching signed request options when script properties are present.
- Docker runtime packaging exists for the API with non-root execution,
  persistent `/data` paths, healthcheck, `.dockerignore`, and CI build
  validation.
- GitHub Actions stable Python CI is passing after the Gmail finalization
  callback error category regression fix.
- Developer setup, current API behavior, and data model notes are documented in
  `docs/development.md`, `docs/api.md`, `docs/addon.md`,
  `docs/deployment.md`, and `docs/data-model.md`.
- Security and privacy boundaries are documented in
  `docs/security-and-privacy.md`.
- Public portfolio readiness boundaries are documented in
  `docs/public-poc-readiness.md`, with open decisions tracked in
  `docs/open-questions.md`.
- ADR 0004 records the product pivot from one-thread preservation into a Gmail
  offloader, inbox cleaner, verified export package, domain/category routing,
  and portable AI/data-port direction.
- ADR 0005 records the local-first-before-SaaS decision, and
  `docs/v0.2-local-first-roadmap.md` breaks that direction into buildable
  milestones.
- `docs/build-log.md` now records each v0.2 implementation step with validation
  evidence.
- v0.2 synthetic classifier seed fixtures exist for newsletter,
  automated/no-reply, bank/financial, human, attachments-heavy, and unknown
  messages.
- v0.2 deterministic classifier rules now map those synthetic fixtures into
  export categories with evidence and review-required gating.

## Setup and Run Commands

```powershell
python -m unittest discover -s tests
python -m pip install -e ".[api,test]"
uvicorn services.api.app.main:app --reload
```

No dependency installation is required for the standard-library contract tests.
The API skeleton requires optional dependencies.

## Gaps Against Target POC

- No deployed Gmail Workspace Add-on or Marketplace package exists yet.
- No HTTPS API entry point exists yet.
- No Google OAuth project or Marketplace add-on configuration is committed; real
  Google verifier validation still belongs in a private environment.
- Browser-backed PDF smoke test is opt-in and not part of default CI yet.
- No deployed live add-on-to-backend archive request flow has been validated
  against a real HTTPS API and OAuth project yet.
- No live Gmail label, mark-read, archive, or callback-success execution has
  been validated with real Workspace Add-on permissions yet.
- No HTTPS deployment target is selected yet.
- No public screenshots, demo video, or hosted synthetic walkthrough has been
  added yet.
- No dry-run batch review, `.eml` writer, local export package writer, or Free
  Space Mode trash/delete queue exists yet.
- No private/public repository split has been executed yet; the recommended
  posture is private core product repo plus public portfolio case study.

## Risky or Conflicting Code

No pre-existing code was present. The main risk is still premature completion:
rendering, storage staging, and Gmail finalization must remain separate until
storage verification and persisted state transitions are implemented. The
archive route tests intentionally keep Gmail finalization disabled. The separate
finalization route tests cover the post-completion handoff.

## Recommended Minimal Changes

1. Finish the public-facing README/docs polish and add synthetic-only screenshots
   or a short walkthrough if the repo will be shared with non-engineers.
2. Design and test the verified export package for raw `.eml`, attachments,
   metadata JSON, readable copy, manifest/checksum files, and normalized text.
3. Add sender-domain/category routing plus dry-run review before any batch
   cleanup behavior.
4. Validate the Google verifier and signed add-on archive/finalization flow
   against a real OAuth client before any real-data demo.
5. Decide the Gmail mutation permission path for label, mark-read, archive,
   trash/delete queue, and callback success behavior.
6. Select and validate the HTTPS deployment target.
