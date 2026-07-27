# ADR 0004: Email Offloader Product Pivot

## Status

Accepted.

## Context

The first POC scope focused on preserving one opened Gmail thread after explicit
confirmation. That foundation produced useful safety boundaries: verified
storage before Gmail mutation, sanitized rendering, generated artifact names,
checksums, audit state, add-on request signing, and disabled Gmail mutation in
the public shell.

The product vision has since clarified. The intended product is broader than a
single-thread archive tool. Email Vault should help users keep valuable email
outside Gmail, reduce inbox noise, optionally free Gmail storage through reviewed
delete/trash workflows, and create portable folders that other tools can search
or analyze.

## Decision

Email Vault will treat the current one-thread preservation path as the
foundational verified export unit. The product direction expands to three
toggleable modes:

1. Preserve Mode: create a verified export package and leave Gmail unchanged.
2. Clean Inbox Mode: create a verified export package, then optionally label,
   archive, or mark read.
3. Free Space Mode: create a verified export package, then move reviewed Gmail
   messages to a trash/delete queue with explicit warnings and a reversible
   window where available.

Verified export means the Preserve Mode package: raw `.eml`, attachments,
metadata JSON, optional readable PDF/HTML, manifest/checksum files, and
normalized text where useful.

Email Vault should organize exports by sender domain, predefined category, or a
mixed user-selected layout. It should expose a portable AI/data port through
files and folders rather than requiring any one downstream AI tool.

## Consequences

- Existing preservation, rendering, storage, signing, and audit boundaries remain
  useful and should not be discarded.
- Whole-mailbox or sender-domain batch behavior must compose verified export
  units instead of bypassing them.
- Gmail archive must not be described as reducing Gmail storage. Storage
  reduction belongs to reviewed trash/delete behavior.
- Delete/free-space behavior is high risk and must remain private/deferred until
  OAuth, consent, review, reversibility, and Gmail API behavior are validated.
- Public portfolio wording should describe the current code as the safety engine
  for the broader offloader/inbox-cleaner product.
