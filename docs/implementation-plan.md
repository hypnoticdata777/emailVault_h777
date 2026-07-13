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
repository protocol boundary, and API tests. SQLite implementation remains next.

## Later Phases

- P3: sanitizer and remote resource blocking.
- P4: storage provider staging and verification.
- P5: PDF renderer with ADR-backed implementation.
- P6: Gmail Add-on flow and finalization callbacks.
