# Public POC Readiness

This checklist separates what is ready for a public portfolio posting from what
must remain private until Google OAuth, deployment, and Gmail permissions are
validated.

The product direction has expanded from one-thread preservation into a Gmail
offloader and inbox cleaner. The current public POC is still the safety engine:
verified preservation before any Gmail cleanup action.

The recommended commercial posture is private core implementation plus public
portfolio case study. The public material should use synthetic screenshots,
architecture notes, and sanitized walkthroughs instead of exposing the full
subscription product implementation.

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
- Product documentation for Preserve Mode, Clean Inbox Mode, Free Space Mode,
  domain/category routing, and the portable AI/data port.
- v0.2 local-first roadmap for one user's Gmail and a user-selected filesystem
  export target.
- v0.2 local-first foundation: export package contracts, deterministic
  classification, dry-run review planning, local package writer, Preserve Mode
  coordinator handoff, and Clean Inbox intent records.
- Local CLI surfaces for Preserve Mode, Clean Inbox dry-run review, and
  post-preservation Clean Inbox intent records.
- Local batch CLI that demonstrates synthetic preserve, review, and lower-risk
  intent recording in one mutation-disabled command.
- Public-safe Markdown report output from the local batch CLI, with absolute
  local package paths omitted.
- Canonical `synthetic-demo` CLI shortcut for the public newsletter,
  bank/financial, and unknown-mail walkthrough.
- Read-only local web demo at `/demo` backed by synthetic data and no mutation
  or file writes.
- Docker runtime boundary for the API.
- Stable Python CI passing in GitHub Actions.
- Documentation for development, API behavior, deployment runtime, data model,
  add-on behavior, security boundaries, and open decisions.
- Synthetic walkthrough for non-engineer portfolio or investor review.

## Must Stay Private Or Deferred

- Real Gmail messages or exports.
- Real OAuth client IDs, tokens, secrets, signing keys, or database credentials.
- Publicly hosted API connected to real Gmail accounts.
- Gmail label, mark-read, archive, or callback-success mutation behavior.
- Gmail trash, delete, permanent delete, or storage-reduction claims.
- Whole-mailbox background sync or batch cleanup.
- Marketplace publication or production Workspace Add-on review.
- Cloud storage or managed database decisions.
- Built-in AI summaries, research, replies, or automation.
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
7. Confirm the README explains that storage savings require delete/trash behavior
   and are not provided by Gmail archive alone.
8. Decide whether the core implementation repo should be switched private before
   adding real Gmail sync, deletion, SaaS billing, or commercial roadmap details.
9. If screenshots are added, confirm they follow the synthetic walkthrough and
   use synthetic data only.
10. Confirm `.local/EmailVault`, local SQLite files, and any generated export
    packages remain untracked.

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
8. Validate domain/category batch routing with dry-run review before cleanup.
9. Validate label, mark-read, archive, trash/delete, and callback-success
   behavior in a private Workspace Add-on deployment before showing real Gmail
   data.
