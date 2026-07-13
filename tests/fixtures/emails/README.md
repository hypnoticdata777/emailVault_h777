# Synthetic Email Fixture Policy

All fixtures in this directory must be synthetic. They may use only `example.com`
addresses, made-up names, harmless placeholder content, and fabricated Gmail
identifiers. Do not copy real email bodies, subjects, filenames, tokens, PDFs,
attachments, or logs into this repository.

Fixtures intentionally include hostile HTML, path traversal filenames, oversized
metadata, and unsupported attachment metadata so the P0/P1 invariant tests can
exercise controlled failures without preserving any real data.

