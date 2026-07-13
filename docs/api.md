# API

This document describes the current P2 API surface. The API is intentionally
small while the preservation pipeline is still being built.

## Authentication

Protected routes require a bearer credential:

```text
Authorization: Bearer synthetic-valid-token
```

The current verifier is synthetic and exists only for local tests. Later phases
must replace it with real Google ID-token verification. Backend ownership must
come from the verified Google identity, never from a request body field.

## `GET /health`

Returns basic service status.

Example response:

```json
{
  "status": "ok",
  "service": "email-vault-api"
}
```

## `POST /archive/thread`

Accepts an `ArchiveThreadRequest` payload representing one opened Gmail thread.

Current P2 behavior:

- Requires bearer identity.
- Validates the request schema and domain invariants.
- Computes a deterministic snapshot fingerprint.
- Checks the configured revision repository for an exact duplicate.
- Returns `DUPLICATE` when the snapshot already exists for the verified owner.
- Returns a controlled `FAILED` stub for new snapshots because rendering,
  storage verification, and durable completed revisions are not implemented yet.
- Always keeps Gmail finalization disabled in P2.

P3 sanitizer work has started, but `/archive/thread` still does not execute a
full preservation pipeline. Sanitized rendering and storage integration remain
future route behavior.

Duplicate response shape:

```json
{
  "status": "DUPLICATE",
  "record": {
    "vault_thread_id": "vault-thread-api-test",
    "revision": 1,
    "record_id": "record-api-test",
    "snapshot_sha256": "..."
  },
  "verification": null,
  "gmail_finalization": {
    "apply_label": "EmailVault/Vaulted",
    "mark_read": false,
    "archive": false,
    "enabled": false
  },
  "error": null
}
```

New-snapshot P2 stub response shape:

```json
{
  "status": "FAILED",
  "record": null,
  "verification": null,
  "gmail_finalization": {
    "apply_label": "EmailVault/Vaulted",
    "mark_read": false,
    "archive": false,
    "enabled": false
  },
  "error": {
    "category": "unexpected_internal_error",
    "message": "Archive execution is not implemented in P2. Gmail finalization is disabled.",
    "field": null
  }
}
```

## Controlled Error Categories

The domain defines controlled categories for authentication, schema validation,
payload limits, unsupported attachments, sanitization/rendering, storage
availability, storage verification, duplicate conflicts, Gmail finalization, and
unexpected internal errors.

## Not Yet Implemented

- Production Google OAuth or Marketplace add-on authentication.
- HTML sanitization and remote-resource blocking.
- PDF rendering.
- Storage provider staging and verification.
- Completed revision writes.
- Gmail label, mark-read, archive, or undo behavior.
