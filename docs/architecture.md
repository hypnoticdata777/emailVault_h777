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
  -> render PDF, metadata, manifest, checksums in temp workspace
  -> StorageProvider.stage_and_verify()
  -> persist audit and revision state
  -> return PRESERVED or DUPLICATE with finalization instructions
Gmail Workspace Add-on
  -> label, optionally mark read/archive
  -> report finalization outcome
```

## Current P1 Layout

```text
services/api/app/core/          Settings and defaults
services/api/app/domain/        Contracts, error categories, state policy
services/api/app/services/      Storage and audit helper boundaries
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

