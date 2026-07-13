# Requirements

## Non-Negotiable Invariants

1. Gmail is not modified before storage verification succeeds.
2. Failure before verification leaves Gmail unchanged.
3. No partial archive is exposed as completed.
4. Exact duplicate submissions do not create duplicate revisions.
5. New messages in an existing Gmail thread create an immutable linked revision.
6. Completed revisions are never overwritten.
7. Protected backend operations derive ownership from verified Google identity.
8. Sensitive email data and tokens never enter application logs.
9. Rendering performs no remote fetches and executes no email JavaScript.
10. Temporary files are deleted on success and every failure path.
11. Stored paths use server-generated trusted identifiers.
12. Public demo and repository use synthetic data only.

## P1 Contract Defaults

- Attachment allowlist: PDF, TXT, CSV, JPEG, PNG.
- Maximum attachments: 10.
- Maximum size per attachment: 10 MB.
- Maximum total payload: 25 MB.
- Exact same snapshot returns the existing record.
- Updated thread creates revision `+1` under the same vault thread.
- Local storage root is configurable.
- SQLite is acceptable locally, with repository boundaries designed for
  Postgres later.

