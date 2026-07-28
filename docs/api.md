# API

This document describes the current API surface. The API is intentionally small
while the preservation pipeline is still being prepared for a public POC.

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

The local web UI has a separate browser-session boundary. `/login/demo` can
open the synthetic demo, while `/login/admin` requires
`EMAIL_VAULT_ADMIN_PASSWORD` and `EMAIL_VAULT_WEB_SESSION_SECRET` before it
sets an HMAC-signed owner session cookie for `/admin`. This is local owner
access only; it is not a replacement for Google OAuth or production account
management.

Archive and Gmail finalization requests may also require add-on request signing.
When `EMAIL_VAULT_ADDON_SIGNING_SECRET` is configured, these mutating routes
expect matching headers:

```text
X-Email-Vault-Timestamp: <unix-seconds>
X-Email-Vault-Signature: <hmac-sha256-hex>
```

The signature covers the HTTP method, path, timestamp, and SHA-256 hash of the
raw request body. Signing is off by default for local development until the
secret is configured.

## `GET /health`

Returns basic service status.

Example response:

```json
{
  "status": "ok",
  "service": "email-vault-api"
}
```

## `GET /demo`

Returns the read-only synthetic local web demo page.

Current behavior:

- Requires no Gmail credentials.
- Uses only the canonical synthetic newsletter, bank/financial, and unknown
  fixtures.
- Shows Clean Inbox review counts, route planning, planned Gmail actions, and
  the canonical CLI command for writing local packages.
- Does not write files, create archive records, label Gmail, mark Gmail read,
  archive Gmail, trash Gmail, or delete Gmail.

## `GET /login`

Returns the local access page with two paths:

- Demo access for the synthetic read-only walkthrough.
- Admin access for the private owner console when local credentials are
  configured.

## `POST /login/demo`

Sets a demo browser session cookie when a web session secret is configured and
redirects to `/demo`. The demo path still uses synthetic data only.

## `POST /login/admin`

Requires both local environment variables:

```text
EMAIL_VAULT_WEB_SESSION_SECRET=<private-local-session-secret>
EMAIL_VAULT_ADMIN_PASSWORD=<private-local-admin-password>
```

On a matching password, it sets an HMAC-signed admin session cookie and
redirects to `/admin`. If either value is missing, admin login is disabled.

## `GET /admin`

Returns the private owner console shell only when the signed admin session is
present. The current page shows the safe live-work status and links back to the
synthetic demo/CLI commands. It also shows private Gmail OAuth readiness:
missing environment variables, configured scopes, and whether mutation-capable
scopes are present. It also shows token-storage readiness for the future
encrypted local token store. It does not connect Gmail, store OAuth tokens, or
execute Gmail cleanup.

## `GET /admin/gmail/oauth/readiness`

Requires the signed admin session. Returns the private read-only Gmail OAuth
configuration status as JSON.

Current readiness checks:

- `GOOGLE_OAUTH_CLIENT_ID` is set and is not the placeholder value.
- `GOOGLE_OAUTH_CLIENT_SECRET` is set outside Git.
- `EMAIL_VAULT_OAUTH_REDIRECT_URI` is present.
- `EMAIL_VAULT_GMAIL_OAUTH_SCOPES` has at least one scope.

Default scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

The endpoint flags mutation-capable Gmail scopes if they are configured, but it
does not start OAuth, exchange tokens, read Gmail, or mutate Gmail.

## `GET /admin/gmail/token-storage/readiness`

Requires the signed admin session. Returns the private token-storage readiness
status as JSON.

Current readiness checks:

- `EMAIL_VAULT_TOKEN_STORE_PATH` is present.
- `EMAIL_VAULT_TOKEN_ENCRYPTION_KEY` is present outside Git.
- plaintext token storage remains disabled.

The endpoint does not store, encrypt, decrypt, or return OAuth token material.

## `GET /oauth/google/callback`

Requires the signed admin session. This is the local OAuth callback shell for
future Google authorization-code handling.

Current behavior:

- reports whether an OAuth error was returned;
- detects whether `code` and `state` query parameters are present;
- deliberately discards the authorization code;
- does not exchange the code for tokens;
- does not store tokens;
- does not read or mutate Gmail.

## `POST /logout`

Clears the local browser session cookie and redirects to `/login`.

## `GET /demo/data`

Returns the same synthetic demo data as JSON for tests or future local UI work.

Example response shape:

```json
{
  "mode": "synthetic_web_demo",
  "gmail_mutation_enabled": false,
  "writes_files": false,
  "summary": {
    "total_threads": 3,
    "review_required_count": 2,
    "approvable_count": 1
  },
  "items": []
}
```

## `POST /archive/thread`

Accepts an `ArchiveThreadRequest` payload representing one opened Gmail thread.

Current behavior:

- Requires bearer identity.
- Validates the request schema and domain invariants.
- Computes a deterministic snapshot fingerprint.
- Checks the configured revision repository for an exact duplicate.
- Returns `DUPLICATE` when the snapshot already exists for the verified owner.
- For new snapshots, prepares a renderer-safe snapshot, renders a PDF through
  the configured renderer adapter, stages and verifies storage, records
  `RENDERED`, `STAGED`, `VERIFIED`, and `COMPLETED`, then returns `PRESERVED`.
- Keeps Gmail finalization disabled on the archive response. Gmail label,
  mark-read, and archive instructions remain behind the separate
  post-completion finalization route.

The current route stores generated PDF, metadata JSON, and manifest JSON
artifacts. It can also store permitted attachment-copy artifacts when the
configured attachment content provider supplies trusted bytes. Signed add-on
requests may provide those bytes as `trusted_content_base64` plus
`content_sha256` on each attachment descriptor. The default provider supplies no
bytes, so normal local API runs remain descriptor-only.

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

## `POST /archive/thread/gmail-finalization`

Requests Gmail finalization instructions for a completed archive record.

Current behavior:

- Requires bearer identity.
- Requires add-on HMAC headers when `EMAIL_VAULT_ADDON_SIGNING_SECRET` is
  configured.
- Looks up the record by verified owner subject plus `record_id`.
- Requires the latest audit state to be `COMPLETED`.
- Appends `GMAIL_FINALIZATION_PENDING`.
- Returns explicit instructions for the add-on to apply the Email Vault label,
  mark read if requested, and archive if requested.

Example request:

```json
{
  "record_id": "record-...",
  "preferences": {
    "category": "Receipts",
    "mark_read_after_preserve": true,
    "archive_after_preserve": true
  }
}
```

Example response:

```json
{
  "record": {
    "vault_thread_id": "vault-thread-...",
    "revision": 1,
    "record_id": "record-...",
    "snapshot_sha256": "..."
  },
  "gmail_finalization": {
    "apply_label": "EmailVault/Vaulted",
    "mark_read": true,
    "archive": true,
    "enabled": true
  },
  "requested_at": "2026-07-14T12:00:00Z"
}
```

## `POST /archive/thread/gmail-finalization/callback`

Records the final Gmail-side result after a pending finalization request.

Current behavior:

- Requires bearer identity.
- Requires add-on HMAC headers when `EMAIL_VAULT_ADDON_SIGNING_SECRET` is
  configured.
- Looks up the record by verified owner subject plus `record_id`.
- Requires the latest audit state to be `GMAIL_FINALIZATION_PENDING`.
- Appends `GMAIL_FINALIZED` when `succeeded` is true.
- Appends `PRESERVED_GMAIL_FINALIZATION_FAILED` when `succeeded` is false.

Example request:

```json
{
  "record_id": "record-...",
  "succeeded": true
}
```

Example response:

```json
{
  "record": {
    "vault_thread_id": "vault-thread-...",
    "revision": 1,
    "record_id": "record-...",
    "snapshot_sha256": "..."
  },
  "state": "GMAIL_FINALIZED",
  "recorded_at": "2026-07-14T12:01:00Z"
}
```

## Controlled Error Categories

The domain defines controlled categories for authentication, schema validation,
payload limits, unsupported attachments, sanitization/rendering, storage
availability, storage verification, duplicate conflicts, Gmail finalization, and
unexpected internal errors.

## Not Yet Implemented

- Google Marketplace packaging and live add-on authentication.
- Live add-on-to-backend validation against a deployed HTTPS API.
- Private-environment validation against a real Google OAuth project.
- Gmail Workspace Add-on label, mark-read, archive, or undo behavior.
