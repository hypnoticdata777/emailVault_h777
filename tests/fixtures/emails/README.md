# Synthetic Email Fixture Policy

All fixtures in this directory must be synthetic. They may use only `example.com`
addresses, made-up names, harmless placeholder content, and fabricated Gmail
identifiers. Do not copy real email bodies, subjects, filenames, tokens, PDFs,
attachments, or logs into this repository.

Fixtures intentionally include hostile HTML, path traversal filenames, oversized
metadata, and unsupported attachment metadata so the P0/P1 invariant tests can
exercise controlled failures without preserving any real data.

v0.2 classifier seed fixtures cover the first local offloader categories:

- `newsletter_digest.json` for newsletter headers such as `List-ID` and
  `List-Unsubscribe`;
- `automated_notice.json` for no-reply and auto-generated mail;
- `bank_notice.json` for financial/review-worthy notices;
- `human_message.json` for direct person-to-person mail;
- `attachments_heavy.json` for messages that should be routed or reviewed
  because they carry several files;
- `unknown_message.json` for ambiguous messages that should default toward
  review instead of automatic cleanup.
