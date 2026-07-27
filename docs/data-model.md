# Data Model

This document explains the core Email Vault nouns in plain language.

## Gmail Thread

A Gmail thread is the conversation container shown by Gmail. It can hold one
message or many messages in the same conversation.

Email Vault archives one opened Gmail thread at a time so the preserved snapshot
matches the user-visible conversation, not just one individual message.

## Message Snapshot

A message snapshot is one email message inside a thread. It includes accessible
metadata such as message identifiers, participants, labels, read state, body
representations, and attachment descriptors.

Message snapshots may also include accessible message headers. v0.2 uses
synthetic header fixtures for explainable classifier signals such as newsletter
list headers and auto-generated message headers. Headers are metadata signals;
they must not contain tokens or secret values in public fixtures.

## Thread Snapshot

A thread snapshot is the canonical request payload for one opened Gmail thread.
It contains the thread identifiers, subject, message list, date range, and
attachment metadata that the integration can access.

The snapshot is not a legal-grade or byte-perfect Gmail export. It is the
complete accessible data that Email Vault can safely normalize.

## Vault Thread

A vault thread is Email Vault's internal grouping for all preserved revisions of
one Gmail thread.

If the same Gmail thread receives a new message later, Email Vault should create
a new revision under the same vault thread instead of overwriting the previous
revision.

## Revision

A revision is an immutable archive attempt for a specific thread snapshot.

Rules:

- Exact duplicate snapshots return the existing record.
- Updated snapshots get `revision + 1`.
- Completed revisions are never overwritten.
- Completion is recorded only after verified preservation state exists.

## Revision Plan

A revision plan is a safe P2 decision object. It can say either:

- this snapshot is an exact duplicate of an existing record; or
- this snapshot should become a new revision later.

The planner may generate server-owned `vault_thread_id` and `record_id` values,
but it does not write a completed record. That write must wait until later phases
can stage artifacts, verify storage, and record the state transition safely.

## Snapshot Fingerprint

The snapshot fingerprint is a deterministic SHA-256 hash of the canonical thread
snapshot. It lets the backend detect exact duplicates without comparing every
field manually.

The fingerprint is scoped by verified owner in persistence. The same synthetic
snapshot hash can exist for two different verified users without becoming a
cross-user conflict.

## Audit Event

An audit event records a state transition for a revision. It is append-only and
ordered. This supports the product invariant that no partial archive should be
exposed as completed.

## What SQLite Stores in P2

The local SQLite repository stores:

- server-generated record identifiers;
- verified owner subject;
- vault thread identifier;
- Gmail thread identifier;
- revision number;
- snapshot fingerprint;
- audit states and timestamps.

It must not store email subjects, bodies, addresses, filenames, PDFs,
attachments, or tokens.

## Stored Artifact

A stored artifact is a generated output such as metadata JSON, attachment
manifest, sanitized PDF, or an allowed attachment copy.

Storage paths use trusted server-generated names. Original attachment filenames
remain metadata only and must never become directory names or storage paths.

## Sanitized Body Representation

A sanitized body representation is a safe body output prepared from an accessible
message body.

Rules:

- `text/html` bodies are sanitized before downstream rendering.
- Remote image sources are blocked.
- Script/style content and event handlers are removed.
- A `text/plain` fallback is always available.
- Original `text/plain` bodies are preserved as plain text.

## Renderer-Safe Snapshot

A renderer-safe snapshot is the sanitized input shape for future PDF rendering.
It includes message metadata plus safe HTML when available and guaranteed plain
text for every message.

The renderer-safe snapshot must not contain raw email HTML. It is a boundary
between sanitization and future rendering work.

## Artifact Manifest Plan

An artifact manifest plan is the safe list of generated outputs that a future
archive revision expects to produce.

The current plan includes:

- a PDF artifact;
- a metadata JSON artifact;
- a manifest JSON artifact.

Each planned artifact uses a server-generated trusted filename. Email subjects,
Gmail identifiers, and original attachment filenames must not become storage
paths.

The plan does not create files, stage storage, or mark a revision completed. It
exists so rendering and storage can be connected later without guessing artifact
names at the last moment.

## Rendered PDF Artifact

A rendered PDF artifact is the renderer output prepared from a renderer-safe
snapshot and an artifact manifest plan.

The current scaffold returns:

- trusted server-generated PDF name;
- content type;
- generated PDF bytes;
- SHA-256 checksum;
- byte size.

It does not stage storage or complete an archive. The real Playwright/Chromium
adapter exists behind the renderer boundary, and storage verification remains
the completion boundary.

## Rendered Artifact Storage Bridge

The rendered artifact storage bridge turns generated PDF bytes into an
`ArtifactToStore` for the storage provider.

It writes the rendered PDF to a temporary source file, calls storage staging and
checksum verification, then removes the temporary source workspace. It does not
write archive state, expose a completed revision, or trigger Gmail
finalization.

## Metadata And Manifest Artifacts

Metadata JSON records sanitized thread metadata, message checksums, preferences,
client context, and attachment copy status. When a trusted provider supplies
bytes, attachment metadata includes the server-generated trusted name and copied
checksum. Without trusted bytes, it remains descriptor-only.

Manifest JSON records the planned artifacts plus generated checksum and byte
size details for the PDF, copied attachments, and metadata JSON. Its own
artifact entry is marked as not yet generated inside the manifest payload to
avoid self-referential checksum claims.

## Export Package Plan

An export package plan is the v0.2 portable offloader contract. It describes the
files Email Vault expects to produce before any inbox cleanup action can run.

The current schema can plan:

- raw `.eml` email output;
- attachment files;
- metadata JSON;
- manifest JSON;
- normalized text;
- optional readable HTML;
- optional readable PDF.

The plan also records the mode: Preserve, Clean Inbox, or Free Space. Preserve
Mode does not allow Gmail cleanup. Clean Inbox and Free Space are cleanup-capable
only after the same verified export package exists.

Folder routing is explicit. A package can use sender-domain folders,
category-first folders, or mixed layouts. Route segments are normalized and
validated so sender-controlled values do not become unsafe paths.

## Export Routing Plan

An export routing plan chooses where a future package should land before any
files are written. It derives the primary sender domain from the thread, accepts
an explicit sender-domain override when the user wants to batch a source
differently, and applies the selected folder layout.

The current routing layer supports:

- domain-first routes such as `example.com/newsletter`;
- category-first routes such as `bank_financial/example.com`;
- mixed routes that push unknown or needs-review messages into review-first
  folders;
- sender-domain overrides for user-controlled batching.

Routing is deterministic and explainable. It does not classify messages by
itself, write files, or mutate Gmail.

## Export Classification Result

An export classification result is the deterministic category decision for a
thread before route planning and dry-run review. It records:

- the selected export category;
- evidence explaining which rule matched;
- whether the category requires user review before cleanup.

The current classifier uses transparent local rules only. It can recognize
newsletter list headers, automated/no-reply signals, bank/financial language,
human question/request language, attachment-heavy messages, and unknown mail.

Bank/financial, human, attachment-heavy, needs-review, and unknown categories
are review-required. Newsletter and automated categories are lower-risk
categories, but future cleanup still must pass through dry-run review and
verified export first.

## Export Dry-Run Plan

An export dry-run plan previews a batch before files are written or Gmail is
changed. It combines classification and route planning into review items.

Each dry-run item records:

- thread identifiers and subject;
- selected export category;
- sender domain and planned export path;
- classifier evidence;
- review-required status;
- planned Gmail action.

The dry-run summary counts items by category, sender domain, export path, and
planned Gmail action.

Preserve Mode plans `export_only`. Clean Inbox Mode plans label/archive actions
only for lower-risk categories and sends risky or unknown categories to
`needs_review`. Free Space Mode never plans direct delete during dry-run; lower
risk items enter a trash review queue, and risky or unknown items stay in
`needs_review`.

## Local Export Package

A local export package is the first filesystem output for the v0.2 offloader
path. It is written under:

```text
<export-root>/<sender-or-category-route>/<record-id>/
```

The writer creates required portable outputs for:

- raw `.eml`;
- metadata JSON;
- normalized text;
- trusted attachment files when attachment bytes are supplied;
- manifest JSON.

The manifest records planned artifacts, generated status, SHA-256 checksum, and
byte size. Optional readable HTML/PDF artifacts can remain planned but skipped
until their generators are connected.

Original attachment filenames stay metadata only. File paths use trusted
server-generated names from the export package plan.

If a required attachment has no trusted bytes, or if size/checksum verification
fails, the writer rejects the package and removes the partial record folder.
This keeps cleanup modes dependent on a verified export package instead of a
best-effort copy.

Preserve Mode can now call the local export package writer from the archive
coordinator. The coordinator converts the verified written package into the
existing storage verification result shape, creates the owner-scoped revision,
records `RENDERED`, `STAGED`, `VERIFIED`, then records `COMPLETED`. Gmail
finalization stays disabled.

## Storage Verification Outcome

A storage verification outcome is the coordinator-level record that storage was
verified for a planned revision.

The current coordinator can:

- create the planned revision only after storage reports `verified=True`;
- append `RENDERED`, `STAGED`, and `VERIFIED` audit events;
- return a verification summary with artifact count, total bytes, and verified
  time.

The archive coordinator can now use this outcome for both the generated
PDF/metadata storage path and the v0.2 local export package path before
recording `COMPLETED`. The archive route still does not return Gmail
finalization instructions from the archive response.

## Archive Completion Outcome

An archive completion outcome records that the backend preservation flow reached
`COMPLETED` after verified storage state exists.

The current coordinator can append `COMPLETED` when the audit history permits a
safe transition from `VERIFIED`. It does not append
`GMAIL_FINALIZATION_PENDING`, return Gmail finalization instructions, or mutate
Gmail.

The archive route can return `PRESERVED` after this completed backend state
exists for the generated PDF, metadata JSON, manifest JSON, and any trusted
permitted attachment-copy artifacts. The v0.2 local Preserve Mode path can also
return `PRESERVED` after the local export package writer has verified raw
`.eml`, metadata JSON, normalized text, manifest JSON, and trusted attachment
outputs.

## Clean Inbox Intent Outcome

A Clean Inbox intent outcome records that the user wants Gmail follow-up after
verified export, without enabling Gmail mutation yet.

It can be recorded only after the archive reaches `COMPLETED`. The coordinator
then appends `CLEAN_INBOX_INTENT_RECORDED` and returns the intended label,
mark-read, and archive preferences with `enabled=false`.

This gives the future UI/API a durable review handoff without claiming Gmail was
changed. A later explicit Gmail finalization request can still move from
`CLEAN_INBOX_INTENT_RECORDED` to `GMAIL_FINALIZATION_PENDING` when mutation
permissions and live validation are ready.

## Gmail Finalization Outcome

Gmail finalization is the post-preservation Gmail mutation boundary. It may
label the thread, mark it read, or archive it, but only after the backend record
has reached `COMPLETED` or a recorded Clean Inbox intent.

The coordinator records two pieces:

- `GMAIL_FINALIZATION_PENDING` when it returns explicit finalization
  instructions for a completed owner-scoped record;
- `GMAIL_FINALIZED` or `PRESERVED_GMAIL_FINALIZATION_FAILED` when the add-on
  reports the callback result.

The owner lookup uses the verified Google subject plus server-generated record
id. A client-supplied record id alone is not trusted.

The API now exposes this as two explicit records of intent: a finalization
request that moves the archive from `COMPLETED` to
`GMAIL_FINALIZATION_PENDING`, and a callback that records either
`GMAIL_FINALIZED` or `PRESERVED_GMAIL_FINALIZATION_FAILED`. The add-on can
request instructions, but actual Gmail label, mark-read, or archive execution
remains a separate permission/deployment step.
