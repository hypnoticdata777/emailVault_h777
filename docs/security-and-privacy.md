# Security and Privacy

Email Vault handles sensitive email data. The public POC must make its safety
boundaries explicit before adding Gmail access, sanitization, rendering, or
storage integration.

## Current P2 Position

The current build uses synthetic fixtures and a synthetic local identity token.
It does not connect to Gmail, fetch real messages, render PDFs, mark messages
read, apply labels, archive Gmail, delete Gmail, or deploy publicly.

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

The P2 verifier is synthetic and accepts only `synthetic-valid-token` for local
tests. Production Google ID-token verification is not implemented yet.

## Gmail Mutation Boundary

Gmail must remain unchanged until backend storage verification succeeds.

The add-on may apply the `EmailVault/Vaulted` label, mark read, or archive only
after the backend returns finalization instructions from a verified preservation
flow. P2 never enables those instructions.

## Storage Boundary

Original filenames are metadata only. Stored paths must use trusted
server-generated names.

The local storage provider can stage generated artifacts and verify checksums,
but it does not mark a revision completed. Completion requires a later service
step that records successful verification and state transition.

## Rendering Boundary

Future HTML rendering must:

- sanitize hostile HTML;
- block remote resources;
- avoid remote network fetches;
- prevent email JavaScript execution;
- provide a plain-text fallback.

This is the next major implementation area in P3.

## Fixtures and Demo Data

The repository and public demo must use synthetic data only. Fixture addresses
should remain under `example.com`, and fixture content must be invented for this
project.

## Secrets

`.env.example` may contain placeholders only. Real OAuth credentials, database
passwords, tokens, and real email exports must not be committed.

## Public-Ready Checklist

Before any public demo:

- replace synthetic identity verification with real Google ID-token
  verification;
- keep demo data synthetic unless a private local-only flow is clearly marked;
- confirm logs redact sensitive fields;
- confirm renderer blocks scripts and remote fetches;
- confirm storage verification happens before Gmail finalization;
- confirm temporary artifacts are removed on success and failure;
- document every known limitation without claiming legal-grade or byte-perfect
  backup.

