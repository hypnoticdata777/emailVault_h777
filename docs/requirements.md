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
13. Cleanup actions are toggles layered after verified export; export must work
    without any Gmail mutation.
14. Free Space Mode must never delete Gmail data before export verification,
    explicit review, warning, and a reversible/trash window where available.
15. Domain/category routing must be explainable and user-overridable before any
    batch cleanup action.
16. AI and downstream data use must work through portable exports, not direct
    mailbox access granted to a specific AI tool by default.

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

## Rescoped Product Defaults

- Preserve Mode exports first and does not change Gmail.
- Clean Inbox Mode exports first, then may label, archive, or mark read.
- Free Space Mode exports first, then may move reviewed messages to a
  trash/delete queue.
- Export packages should support raw `.eml`, attachments, metadata JSON,
  optional readable PDF/HTML, manifest/checksum files, and normalized text.
- Folder routing should support sender-domain folders, predefined categories,
  and user overrides.
- Public portfolio demos must show synthetic email only and should avoid claims
  that Gmail storage is reduced unless deletion/trash behavior is explicitly
  enabled and validated.
