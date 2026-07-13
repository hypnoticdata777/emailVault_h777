# Implementation Plan

## P0 Complete

- Audit the repository.
- Freeze the POC scope.
- Record transaction boundary and initial architecture decisions.

## P1 Complete

- Define canonical contracts, state enum, and controlled error categories.
- Add typed settings and `.env.example`.
- Add synthetic fixtures and fixture policy.
- Add foundational invariant tests.

## P2 In Progress

- Add FastAPI and Pydantic v2 request/response models.
- Add Google ID token verification interface and test doubles.
- Add repository interfaces and SQLite-backed revision/audit persistence.

Current P2 scope adds the API app, Pydantic schemas, identity verifier boundary,
repository protocol boundary, SQLite persistence, and API/repository tests.

The P2 orchestration layer now uses verified identity, validation, fingerprinting,
repository duplicate lookup, and controlled errors without invoking any renderer,
storage provider, durable write, or Gmail finalization.

The route now uses the configured SQLite repository by default, and local setup
has a minimal bootstrap command: `python -m services.api.app.cli init-db`.
Companion docs now cover local development, current API behavior, and the core
data model.

The safe revision planner now prepares duplicate or new-revision decisions
without writing completed records. It reuses the existing vault thread for
updated Gmail threads and generates server-owned IDs for new vault threads.

The first explicit storage provider boundary now stages generated artifacts and
verifies checksums in local development without marking revisions completed.

Security and privacy boundaries are documented for public-ready development.

P3 has started with dependency-light HTML sanitization, remote image-source
blocking, script/style content removal, plain-text fallback, normalized
sanitized body output, renderer-safe snapshot preparation, coverage for
table-heavy plus attachment-adjacent HTML, and artifact manifest planning for
future generated outputs. The PDF renderer boundary is now recorded in ADR
0003 before renderer implementation begins. The first renderer scaffold now
uses an adapter boundary so tests can verify sanitized input, disabled
JavaScript, blocked network policy, PDF artifact bytes, and temporary workspace
cleanup. The Playwright/Chromium adapter boundary is wired behind that scaffold
with tests for JavaScript-disabled contexts, route abortion, PDF options, and
browser resource cleanup. An opt-in browser-backed smoke test path now verifies
local Chromium PDF rendering when renderer dependencies are installed and
`EMAIL_VAULT_RUN_RENDERER_SMOKE=1` is set. Rendered PDF output can now be
staged through the storage provider and checksum verified without recording a
completed revision. The coordinator can now create the planned revision after
verified storage and append `RENDERED`, `STAGED`, and `VERIFIED` audit events
without enabling Gmail finalization. It can also append `COMPLETED` after the
verified storage state transition, still without enabling Gmail finalization.
The coordinator can now request Gmail finalization only from a completed
owner-scoped record and record callback success or failure only after
`GMAIL_FINALIZATION_PENDING`. GitHub Actions CI now runs the stable Python 3.12
test suite with API/test dependencies on push and pull request while keeping the
browser-backed renderer smoke test opt-in. The identity boundary now supports
selectable local synthetic verification or Google ID-token verification for a
configured OAuth client ID, with tests covering the verifier without calling
Google. The first Gmail Workspace Add-on shell now exists as preview-only Apps
Script files with tests for the contextual trigger, minimal current-message
scopes, expected entry points, dormant request-signing helpers, and absence of
Gmail mutation or backend fetch calls. Docker runtime packaging now exists for
the API, with CI building the image to keep the runtime boundary from drifting.
The archive route now calls the completed backend preservation path for
generated PDF, metadata JSON, and manifest JSON output and returns `PRESERVED`
after verified storage plus `COMPLETED`, while Gmail finalization remains
disabled. Trusted permitted attachment copy now exists behind an injectable
content provider; default route behavior remains descriptor-only until Gmail
fetch wiring supplies bytes. The API can now verify add-on HMAC request
signatures when `EMAIL_VAULT_ADDON_SIGNING_SECRET` is set, but the add-on still
does not execute live backend archive requests.

## Later Phases

- P6: wire Gmail attachment fetch bytes into the trusted content provider.
- P7: add-on-to-backend request execution, HTTPS deployment choice, and private
  OAuth validation.
