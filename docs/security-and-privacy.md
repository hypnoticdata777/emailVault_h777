# Security and Privacy

Email Vault handles sensitive email data. The public POC must make its safety
boundaries explicit before adding Gmail access, sanitization, rendering, or
storage integration.

## Current Position

The current build uses synthetic fixtures and defaults to a synthetic local
identity token. It can be configured to verify Google ID tokens, but it does not
connect to Gmail, fetch real messages, render PDFs from the API route, mark
messages read, apply labels, archive Gmail, delete Gmail, or deploy publicly.

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

## Gmail Mutation Boundary

Gmail must remain unchanged until backend storage verification succeeds.

The add-on may apply the `EmailVault/Vaulted` label, mark read, or archive only
after the backend returns finalization instructions from a verified preservation
flow. The current archive route still does not enable those instructions.

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

Artifact planning must use generated filenames for future PDF, metadata JSON,
and manifest JSON outputs. Email-controlled fields such as subjects, Gmail
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

Gmail finalization instructions may now be requested only for a completed record
owned by the verified Google subject. The callback result may be recorded only
after `GMAIL_FINALIZATION_PENDING`, and the callback records success as
`GMAIL_FINALIZED` or failure as `PRESERVED_GMAIL_FINALIZATION_FAILED`.

## Fixtures and Demo Data

The repository and public demo must use synthetic data only. Fixture addresses
should remain under `example.com`, and fixture content must be invented for this
project.

## Secrets

`.env.example` may contain placeholders only. Real OAuth credentials, database
passwords, tokens, and real email exports must not be committed.

## Public-Ready Checklist

Before any public demo:

- configure and validate Google ID-token verification against a real OAuth
  client ID in a private environment;
- keep demo data synthetic unless a private local-only flow is clearly marked;
- confirm logs redact sensitive fields;
- confirm renderer blocks scripts and remote fetches;
- confirm storage verification happens before Gmail finalization;
- confirm temporary artifacts are removed on success and failure;
- document every known limitation without claiming legal-grade or byte-perfect
  backup.
