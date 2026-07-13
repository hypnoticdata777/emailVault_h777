# Product Scope

Email Vault v0.1 preserves the accessible snapshot of one currently opened Gmail
thread after explicit user confirmation. It produces a sanitized PDF, structured
metadata JSON, attachment manifest, and permitted attachments. Gmail must remain
unchanged until backend storage verification succeeds.

## Included in v0.1

- One opened Gmail thread per operation.
- Workspace Add-on sidebar preview and explicit confirmation.
- Category plus optional mark-read/archive preferences.
- Accessible headers, labels, message states, participants, bodies, and allowed
  attachments.
- HTML sanitization, remote-resource blocking, and plain-text fallback.
- Immutable revisions, duplicate detection, audit history, and verified storage.
- Synthetic fixtures and tests only.

## Excluded from v0.1

- Whole-mailbox batch processing.
- Background surveillance.
- Gmail deletion.
- Arbitrary attachment formats.
- AI summaries, generated replies, forwarding, or anomaly detection.
- Multiple mail providers, subscriptions, team accounts, Marketplace release, or
  direct cloud-to-USB writing.

## Product Wording

The product preserves the complete data that the selected integration can access
and safely normalize. It must not claim legal-grade or byte-perfect backup.

