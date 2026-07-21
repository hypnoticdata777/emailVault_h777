# Public POC Readiness

This checklist separates what is ready for a public portfolio posting from what
must remain private until Google OAuth, deployment, and Gmail permissions are
validated.

## Ready For Public Portfolio Review

- Synthetic fixtures and invented `example.com` data only.
- Canonical thread archive contracts, state model, and controlled error
  categories.
- FastAPI archive and Gmail finalization route boundaries.
- SQLite-backed owner-scoped revision and audit persistence for the POC.
- Sanitized renderer-safe snapshots and generated archive artifact planning.
- PDF rendering boundary with JavaScript disabled and network requests blocked.
- Local storage staging with checksum verification.
- Metadata JSON and manifest JSON output.
- Trusted attachment byte-copy path behind backend verification.
- Gmail Workspace Add-on shell with preference capture and signed backend helper
  calls.
- Explicit no-mutation Gmail posture in the current add-on shell.
- Docker runtime boundary for the API.
- Stable Python CI passing in GitHub Actions.
- Documentation for development, API behavior, deployment runtime, data model,
  add-on behavior, security boundaries, and open decisions.

## Must Stay Private Or Deferred

- Real Gmail messages or exports.
- Real OAuth client IDs, tokens, secrets, signing keys, or database credentials.
- Publicly hosted API connected to real Gmail accounts.
- Gmail label, mark-read, archive, or callback-success mutation behavior.
- Marketplace publication or production Workspace Add-on review.
- Cloud storage or managed database decisions.
- Any claim that the POC is a production backup, legal hold, or byte-perfect
  archival product.

## Before Posting The Repo Publicly

1. Confirm GitHub Actions is green on the latest main commit.
2. Confirm `.env.example` contains placeholders only.
3. Confirm no local SQLite database, generated PDF, rendered artifact, or
   storage directory is tracked.
4. Confirm README and docs describe Gmail mutation as disabled.
5. Confirm screenshots, if added, use synthetic data only.
6. Confirm known limitations are visible from the README.

## Before A Live Hosted Demo

1. Choose an HTTPS deployment target.
2. Decide whether SQLite is acceptable for the demo or switch to managed
   persistence.
3. Configure `EMAIL_VAULT_IDENTITY_VERIFIER=google` privately.
4. Configure a real `GOOGLE_OAUTH_CLIENT_ID` privately.
5. Configure `EMAIL_VAULT_ADDON_SIGNING_SECRET` privately.
6. Validate signed add-on archive and finalization calls against the deployed
   API.
7. Decide Gmail mutation scopes and consent copy.
8. Validate label, mark-read, archive, and callback-success behavior in a
   private Workspace Add-on deployment before showing real Gmail data.
