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
- P2 does not write completed revisions because storage verification does not
  exist yet.

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
