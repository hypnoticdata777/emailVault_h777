# Open Questions

This file tracks product and deployment decisions that still need a human
answer. Defaults are acceptable for local development and portfolio review, but
private Google and deployment choices must be made before any real Gmail data or
live add-on demo.

## Answered For The Public Portfolio POC

1. Should Gmail be mutated by the default archive route?
   - Answer: no.
   - Current behavior: `/archive/thread` preserves the backend snapshot and
     leaves Gmail finalization disabled. Label, mark-read, and archive behavior
     stay behind a separate post-completion finalization boundary.

2. Should the project use synthetic or real email data in the public repo?
   - Answer: synthetic only.
   - Current behavior: fixtures use `example.com` data and invented content.
     Real email exports, OAuth tokens, local databases, and generated archive
     artifacts must stay out of Git.

3. Should local development use SQLite?
   - Answer: yes for the POC.
   - Current behavior: local development can use `sqlite:///./email_vault.db`;
     Docker runtime defaults to `/data/email_vault.db` so local runtime data can
     be mounted outside the image.

4. Should storage use local filesystem or cloud storage for the portfolio POC?
   - Answer: local filesystem for now.
   - Current behavior: the local storage provider stages generated artifacts and
     verifies checksums. Cloud storage is intentionally deferred until the
     deployment target is chosen.

5. Should archive categories be free-form or controlled?
   - Answer: archive preference categories remain free-form for now.
   - Current behavior: controlled categories are used for API errors and state
     transitions. User-facing archive preference categories remain strings so
     the contract does not block early product exploration.

## Still Pending Before A Live Public Demo

1. Which Google OAuth client ID will be used for the add-on?
   - Required before: production-like identity verification or real Gmail
     testing.
   - Current default: placeholder only in `.env.example`; real client IDs stay
     outside Git.

2. Which HTTPS deployment target should host the API?
   - Required before: deployed add-on-to-backend validation.
   - Current default: undecided. The Docker runtime is ready to package the API,
     but no hosting provider is committed.

3. Is SQLite acceptable for the deployed demo?
   - Required before: selecting the public demo architecture.
   - Current default: SQLite is acceptable for local and private POC validation.
     A managed database should be considered if the hosted demo has multiple
     users or persistent public traffic.

4. Which Gmail mutation permissions should be requested?
   - Required before: applying labels, marking messages read, archiving Gmail
     messages, or recording callback success after live mutation.
   - Current default: no Gmail mutation. Keep the add-on read/current-message
     oriented until permission copy, scope review, and private validation are
     complete.

5. What public demo posture should be used?
   - Required before: investor/portfolio posting.
   - Recommended default: public code repo plus README walkthrough first; live
     hosted API/add-on demo only after private OAuth and HTTPS validation.
