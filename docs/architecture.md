# Architecture

## POC Boundary

The transaction boundary is the storage verification result. Gmail labeling,
mark-read, and archive operations are not permitted until the backend has staged
artifacts, verified durable storage, and recorded the revision state.

## Preferred Flow

```text
Gmail Workspace Add-on
  -> HTTPS API with Google ID token and canonical thread payload
API
  -> verify identity and resolve internal user
  -> validate payload and enforce limits
  -> detect duplicate or revision
  -> sanitize HTML and block remote resources
  -> plan generated artifact manifest with trusted filenames
  -> render generated PDF in temp workspace
  -> StorageProvider.stage_and_verify()
  -> persist audit and revision state
  -> return PRESERVED or DUPLICATE with Gmail finalization disabled
Gmail Workspace Add-on
  -> later request finalization instructions
  -> label, optionally mark read/archive only after instructions
  -> report finalization outcome
```

## Current P1 Layout

```text
services/api/app/core/          Settings and defaults
services/api/app/domain/        Contracts, error categories, state policy
services/api/app/services/      Archive, revision planning, storage boundaries
tests/fixtures/emails/          Synthetic canonical and security fixtures
docs/adr/                       Architecture decision records
```

## Security Boundaries

- Ownership must come from a verified Google identity, never a client-supplied
  owner ID.
- Original filenames are metadata only. Stored paths must be server generated.
- Logs must exclude subjects, bodies, addresses, filenames, PDFs, attachments,
  and tokens.
- Rendering must not execute email JavaScript or fetch remote resources.

See `docs/security-and-privacy.md` for the fuller public-ready safety model.
See `docs/adr/0003-pdf-renderer-boundary.md` for the PDF renderer decision.

## Storage Boundary

The storage provider boundary stages generated artifacts and verifies checksums.
It does not decide that a revision is completed and it never triggers Gmail
finalization. Later phases must call storage only after sanitization/rendering
has produced safe artifacts, then persist state only after verification succeeds.

## Artifact Planning Boundary

The artifact manifest planner names the generated outputs before rendering or
storage begins. It currently plans a PDF, metadata JSON, and manifest JSON with
server-generated filenames only.

This keeps artifact identity out of email-controlled fields and gives later
renderer/storage integration a stable contract without claiming that any file
has been produced or verified yet.

## PDF Rendering Boundary

ADR 0003 selects a Playwright/Chromium-based renderer for the POC, with email
JavaScript disabled and every network request blocked. The renderer must consume
renderer-safe snapshots only, write generated outputs into a temporary
workspace, and clean that workspace on success and failure.

The current renderer scaffold keeps Playwright behind an adapter boundary. It
builds renderer HTML from `RendererSafeThreadSnapshot`, applies a policy with
JavaScript disabled and network blocking enabled, reads generated PDF bytes, and
cleans the temporary workspace before returning.

The Playwright adapter boundary creates a Chromium context with JavaScript
disabled, registers a route handler that aborts network requests, renders the
safe HTML to PDF, and closes browser resources.

Rendering a PDF is not enough to complete an archive. Completion still requires
storage staging, checksum verification, persisted state, and only then Gmail
finalization instructions.

## Renderer To Storage Boundary

Rendered PDF output can now be handed to the storage provider as a generated
artifact. The bridge writes the PDF bytes to a temporary source file, calls
`StorageProvider.stage_and_verify()`, and cleans the temporary source workspace
on success or failure.

The bridge returns storage verification details only. Persisting `VERIFIED` or
`COMPLETED` state remains a coordinator decision.

## Verified Storage State Boundary

The archive coordinator can now record a verified storage result by creating the
planned revision and appending `RENDERED`, `STAGED`, and `VERIFIED` audit
events. Completion remains a separate transition so storage verification cannot
accidentally imply Gmail finalization.

## Completion State Boundary

The archive coordinator can now append `COMPLETED` after the latest audit state
is allowed to transition from verified preservation into completion. This marks
the backend archive record complete, but it still does not create Gmail
finalization instructions.

Gmail labeling, mark-read, and archive actions remain a later callback boundary
so the public POC can prove preservation completion before mutating Gmail.

## Archive Route Preservation Boundary

`POST /archive/thread` now calls the backend preservation path for generated PDF
output. It validates ownership, checks duplicates, prepares sanitized renderer
input, renders the PDF through the configured adapter, stages and verifies
storage, appends `COMPLETED`, and returns `PRESERVED`.

The route still returns Gmail finalization disabled. Finalization instructions
remain a separate owner-scoped call after completion.

## Gmail Finalization Boundary

The archive coordinator can now request Gmail finalization only after the owner
scoped record has reached `COMPLETED`. Requesting finalization appends
`GMAIL_FINALIZATION_PENDING` and returns explicit instructions for label,
mark-read, and archive actions.

The callback result is recorded only after finalization is pending. Success
appends `GMAIL_FINALIZED`; failure appends
`PRESERVED_GMAIL_FINALIZATION_FAILED`. The coordinator looks up records by the
verified Google subject plus record id so a client-supplied record id cannot
cross owner boundaries.
