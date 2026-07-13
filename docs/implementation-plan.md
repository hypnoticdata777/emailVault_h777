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
future generated outputs.

## Later Phases

- P3: write the PDF renderer ADR before implementing rendering.
- P4: connect renderer output to storage staging and verification.
- P5: record completion state transitions only after storage verification.
- P6: Gmail Add-on flow and finalization callbacks.
