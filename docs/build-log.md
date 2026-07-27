# Build Log

This log records the major implementation steps so the project history remains
easy to follow alongside Git commits.

## 2026-07-27 - v0.2 Export Package Schema

- Added the local-first export package contract for Preserve, Clean Inbox, and
  Free Space modes.
- Planned portable artifacts for raw `.eml`, metadata JSON, manifest JSON,
  normalized text, optional readable HTML/PDF, and attachments.
- Added cleanup gating so Preserve Mode cannot trigger Gmail cleanup.
- Documented export package data model and traceability.
- Validation: `python -m unittest discover -s tests` passed with 124 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Export Route Planning

- Added deterministic sender-domain and category route planning.
- Supported domain-first, category-first, and mixed review-first folder layouts.
- Added sender-domain overrides for user-controlled batching.
- Documented export routing in the data model and traceability.
- Validation: `python -m unittest discover -s tests` passed with 131 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Classifier Seed Fixtures

- Added synthetic fixtures for newsletter, automated/no-reply, bank/financial,
  human, attachments-heavy, and unknown messages.
- Added safe message header support so future classifier rules can inspect
  newsletter and automated-message signals.
- Kept fixtures synthetic with `example.com` addresses and invented content.
- Updated the fixture policy and roadmap status.
- Validation: `python -m unittest discover -s tests` passed with 133 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Deterministic Classifier Rules

- Added transparent local classifier rules for newsletter headers,
  automated/no-reply senders, bank/financial language, human questions,
  attachment-heavy messages, and unknown mail.
- Added classifier evidence so future dry-run review can explain why each
  message was routed into a category.
- Added review-required gating for bank/financial, human, attachment-heavy,
  needs-review, and unknown categories while newsletter and automated mail stay
  eligible for lower-risk cleanup review.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 141 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Dry-Run Review Planning

- Added dry-run review objects that combine classifier results, sender-domain
  routing, export paths, and planned Gmail actions without writing files or
  mutating Gmail.
- Added summary counts by category, sender domain, export path, and planned
  Gmail action so a future review UI can show batch impact before cleanup.
- Kept risky or unknown categories in `needs_review` for Clean Inbox Mode, and
  kept Free Space Mode behind review-only trash queue planning.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 146 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Local Export Package Writer

- Added a local export package writer that writes planned packages under the
  selected export root, sender/category route, and server-owned record folder.
- Generated required portable outputs for raw `.eml`, metadata JSON,
  normalized text, trusted attachment files, and export manifest JSON.
- Added checksum and size verification for every generated file, while keeping
  original attachment filenames as metadata only.
- Rejected missing or mismatched trusted attachment bytes and cleaned partial
  package folders on failure.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 151 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Preserve Mode Export Package Boundary

- Wired Preserve Mode through the local export package writer at the archive
  coordinator layer.
- Reused the existing verified-storage and completed-preservation audit
  boundary so local packages can record `RENDERED`, `STAGED`, `VERIFIED`, and
  `COMPLETED` only after checksum-verified output exists.
- Kept Gmail finalization disabled on Preserve Mode responses.
- Added tests for successful local package preservation, duplicate short-circuit
  behavior, and missing attachment-byte rejection without archive state writes.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 154 tests and
  17 expected skips.
