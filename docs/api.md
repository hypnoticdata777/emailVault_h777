# API

This document describes the current P2 API surface. The API is intentionally
small while the preservation pipeline is still being built.

## Authentication

Protected routes require a bearer credential:

```text
Authorization: Bearer synthetic-valid-token
```

By default, local development uses the synthetic verifier and accepts only
`synthetic-valid-token`. Production-like verification can be selected with
`EMAIL_VAULT_IDENTITY_VERIFIER=google` and a configured
`GOOGLE_OAUTH_CLIENT_ID`; in that mode, the bearer credential must be a Google
ID token issued for the configured OAuth client ID.

Backend ownership must come from the verified Google identity, never from a
request body field.

Archive requests may also require add-on request signing. When
`EMAIL_VAULT_ADDON_SIGNING_SECRET` is configured, `POST /archive/thread` expects
these headers:

```text
X-Email-Vault-Timestamp: <unix-seconds>
X-Email-Vault-Signature: <hmac-sha256-hex>
```

The signature covers the HTTP method, path, timestamp, and SHA-256 hash of the
raw request body. This is dormant by default for local development until the
add-on-to-backend flow is wired.

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
- For new snapshots, prepares a renderer-safe snapshot, renders a PDF through
  the configured renderer adapter, stages and verifies storage, records
  `RENDERED`, `STAGED`, `VERIFIED`, and `COMPLETED`, then returns `PRESERVED`.
- Keeps Gmail finalization disabled. Gmail label, mark-read, and archive
  instructions remain behind the separate post-completion finalization boundary.

The current route stores generated PDF, metadata JSON, and manifest JSON
artifacts. It can also store permitted attachment-copy artifacts when the
configured attachment content provider supplies trusted bytes. The default
provider supplies no bytes, so normal local API runs remain descriptor-only
until add-on or backend Gmail fetch wiring exists.

The service layer now has the Gmail finalization boundary used by future API
routes: instructions can be requested only after `COMPLETED`, and callback
results can be recorded only after `GMAIL_FINALIZATION_PENDING`.

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

New-snapshot preserved response shape:

```json
{
  "status": "PRESERVED",
  "record": {
    "vault_thread_id": "vault-thread-...",
    "revision": 1,
    "record_id": "record-...",
    "snapshot_sha256": "..."
  },
  "verification": {
    "verified": true,
    "artifact_count": 3,
    "total_bytes": 12345,
    "verified_at": "2026-07-13T19:00:00Z"
  },
  "gmail_finalization": {
    "apply_label": "EmailVault/Vaulted",
    "mark_read": false,
    "archive": false,
    "enabled": false
  },
  "error": null
}
```

## Controlled Error Categories

The domain defines controlled categories for authentication, schema validation,
payload limits, unsupported attachments, sanitization/rendering, storage
availability, storage verification, duplicate conflicts, Gmail finalization, and
unexpected internal errors.

## Not Yet Implemented

- Google Marketplace packaging and live add-on authentication.
- Add-on-to-backend archive request execution.
- Private-environment validation against a real Google OAuth project.
- Gmail attachment fetch integration for the trusted attachment content provider.
- Gmail Workspace Add-on label, mark-read, archive, or undo behavior.
