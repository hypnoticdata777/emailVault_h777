# Security and Privacy

Email Vault handles sensitive email data. The public POC must make its safety
boundaries explicit before adding Gmail access, sanitization, rendering, or
storage integration.

## Current Position

The current backend uses synthetic fixtures and defaults to a synthetic local
identity token. It can be configured to verify Google ID tokens. The archive
route can render and preserve the generated PDF path, and the repository also
includes a Gmail Add-on shell that can call the backend with signed request
headers when script properties are configured. The API also exposes signed
Gmail finalization request and callback routes. The project does not deploy
publicly, mark messages read, apply labels, archive Gmail, or delete Gmail.

The local web access layer now separates synthetic demo access from an
owner-only admin console. Admin login requires local environment variables for
the password and HMAC session secret. This protects the local owner console
during development, but it is not production multi-user authentication and does
not replace Google OAuth verification.

The admin console can report Gmail OAuth readiness for the private read-only
scope. Readiness does not exchange tokens, read Gmail, or grant Gmail mutation.
Mutation-capable scopes must remain out of the default local configuration until
the review and consent path is designed.

## Data That Must Not Enter Logs

Application logs must not contain:

- email subjects;
- message bodies;
- email addresses;
- display names;
- original attachment filenames;
- attachment content;
- generated PDFs;
- OAuth tokens or ID tokens;
- admin passwords or session secrets;
- raw Gmail payloads.

Logs should use request IDs, record IDs, state names, controlled error
categories, counts, byte sizes, and server-generated identifiers instead.

## Identity and Ownership

Protected backend behavior must derive ownership from a verified Google
identity. The client must never send an owner ID that the backend trusts.

Local development defaults to the synthetic verifier and accepts only
`synthetic-valid-token` for tests. Production-like mode must set
`EMAIL_VAULT_IDENTITY_VERIFIER=google` and `GOOGLE_OAUTH_CLIENT_ID` so backend
ownership is derived from Google ID-token claims verified for that configured
client ID.

When add-on request signing is configured, archive and Gmail finalization routes
also require a fresh HMAC signature over the method, path, timestamp, and raw
request body hash. This does not replace Google identity; it reduces accidental
or replayed add-on-to-backend calls once the live add-on execution path exists.

The add-on may read attachment bytes only to include them in the signed archive
request payload with SHA-256 checksums. The backend must still verify size and
checksum before copying those bytes under server-generated names.

## Gmail Mutation Boundary

Gmail must remain unchanged until backend storage verification succeeds.

The add-on may apply the `EmailVault/Vaulted` label, mark read, or archive only
after the backend returns finalization instructions from a verified preservation
flow. The archive route can complete backend preservation, but it still does not
return those Gmail instructions. The separate finalization route returns
instructions only after owner-scoped `COMPLETED` state.

## Storage Boundary

Original filenames are metadata only. Stored paths must use trusted
server-generated names.

The local storage provider can stage generated artifacts and verify checksums,
but it does not mark a revision completed. Completion requires a later service
step that records successful verification and state transition.

## Sanitization and Rendering Boundary

HTML sanitization must:

- sanitize hostile HTML;
- block remote resources;
- prevent email JavaScript execution;
- provide a plain-text fallback.

Future rendering must avoid remote network fetches and must consume sanitized
content, not raw email HTML.

P3 now includes normalized sanitized body output so downstream rendering can use
safe HTML and guaranteed plain text instead of raw message bodies.

Renderer-safe snapshots must consume sanitized bodies only. Raw email HTML should
not cross into renderer inputs.

Table-heavy emails and attachment-adjacent HTML links must preserve visible text
while stripping unsafe attributes or unsafe link targets such as `file:` and
`data:`.

Artifact planning must use generated filenames for PDF, metadata JSON, and
manifest JSON outputs. Email-controlled fields such as subjects, Gmail
identifiers, and original attachment filenames must not become storage paths.

Rendered PDF storage staging must remain separate from archive completion. A
verified checksum proves the local storage copy succeeded, but it does not by
itself permit Gmail labeling, mark-read, or archive operations.

Coordinator audit may record `VERIFIED` after storage succeeds. Gmail
finalization still requires a later completed-preservation step and must not be
enabled from `VERIFIED` alone.

Coordinator audit may now record `COMPLETED` after the verified storage state
transition. `COMPLETED` means the backend preservation record is finished; it
grants permission to request finalization instructions only through the
owner-scoped coordinator boundary.

Metadata JSON and manifest JSON may be staged with the generated PDF. Permitted
attachments may be copied only through the trusted attachment content provider,
with size/checksum verification and server-generated stored names. Original
filenames stay metadata only. When trusted bytes are unavailable, attachment
records remain descriptor-only.

Gmail finalization instructions may now be requested only for a completed record
owned by the verified Google subject. The callback result may be recorded only
after `GMAIL_FINALIZATION_PENDING`, and the callback records success as
`GMAIL_FINALIZED` or failure as `PRESERVED_GMAIL_FINALIZATION_FAILED`.

The add-on currently requests finalization instructions but does not execute
label, mark-read, or archive actions. Callback success should not be wired until
the Gmail mutation scopes, user-facing consent copy, and private deployment
validation are complete.

## Fixtures and Demo Data

The repository and public demo must use synthetic data only. Fixture addresses
should remain under `example.com`, and fixture content must be invented for this
project.

## Secrets

`.env.example` may contain placeholders only. Real OAuth credentials, database
passwords, tokens, and real email exports must not be committed.

`EMAIL_VAULT_WEB_SESSION_SECRET` and `EMAIL_VAULT_ADMIN_PASSWORD` are local
owner secrets. They belong in the user's environment or private hosting secret
store only.

`GOOGLE_OAUTH_CLIENT_SECRET` is also a private secret and must not be committed.
The default Gmail OAuth scope should remain
`https://www.googleapis.com/auth/gmail.readonly` until live cleanup behavior is
explicitly approved and tested.

## Public-Ready Checklist

Before any public demo:

- configure and validate Google ID-token verification against a real OAuth
  client ID in a private environment;
- keep demo data synthetic unless a private local-only flow is clearly marked;
- confirm logs redact sensitive fields;
- confirm admin/demo access uses synthetic data publicly and keeps owner
  credentials private;
- confirm renderer blocks scripts and remote fetches;
- confirm storage verification happens before Gmail finalization;
- confirm Gmail mutation scopes and callback success behavior are validated in a
  private Workspace Add-on deployment;
- confirm temporary artifacts are removed on success and failure;
- document every known limitation without claiming legal-grade or byte-perfect
  backup.
