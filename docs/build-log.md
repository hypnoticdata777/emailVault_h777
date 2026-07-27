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
