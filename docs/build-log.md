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

## 2026-07-27 - v0.2 Clean Inbox Intent Records

- Added `CLEAN_INBOX_INTENT_RECORDED` as a post-completion archive state.
- Added an archive coordinator method that records Clean Inbox intent after a
  completed archive while returning Gmail cleanup instructions with
  `enabled=false`.
- Preserved the explicit Gmail finalization boundary: live label/archive/mark
  read instructions still require the separate finalization request path.
- Added tests for completed-only intent recording, disabled mutation
  instructions, pre-completion rejection, and later explicit finalization.
- Updated roadmap, data model, traceability, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - v0.2 Closeout And Public POC Readiness Sweep

- Added a v0.2 closeout and next-wave document that records what the
  local-first implementation now proves.
- Updated README and implementation plan so they no longer describe v0.2
  foundation work as future work.
- Refreshed public POC readiness notes with the completed v0.2 foundation and
  the next recommended blockers.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - Synthetic Walkthrough For Public Review

- Added a public-safe synthetic walkthrough for portfolio, investor, and
  non-engineer review.
- Documented the demo story from Gmail batch preview through classification,
  dry-run review, verified local export package, and Clean Inbox intent.
- Added a screenshot checklist and short public demo script that avoid real
  Gmail data and live mutation claims.
- Updated README, public POC readiness, closeout, and current-state audit notes.
- Validation: `python -m unittest discover -s tests` passed with 157 tests and
  17 expected skips.

## 2026-07-27 - Local Preserve Mode CLI

- Added `python -m services.api.app.cli preserve-local` as the first hands-on
  local Preserve Mode interface.
- The command accepts an archive request JSON file, selected export root,
  optional trusted attachment byte mappings, and folder layout controls.
- It reuses the archive coordinator local export package path and prints status,
  record id, package path, verification count, byte total, and Gmail
  finalization status.
- Added CLI tests for database bootstrap, successful local package export,
  duplicate short-circuit behavior, and controlled missing-attachment failures.
- Updated README, development docs, closeout notes, and current-state audit.
- Validation: `python -m unittest discover -s tests` passed with 161 tests and
  17 expected skips.

## 2026-07-27 - Local Clean Inbox Review CLI

- Added `python -m services.api.app.cli clean-inbox-review` so local demos can
  preview Clean Inbox category, sender-domain route, export path, planned Gmail
  action, review-required flag, and classifier evidence for one or more
  synthetic request files.
- Added `python -m services.api.app.cli record-clean-inbox-intent` so completed
  Preserve Mode records can receive a local `CLEAN_INBOX_INTENT_RECORDED` audit
  marker.
- Kept Gmail mutation disabled in both commands. The review command does not
  write files, and the intent command returns Gmail finalization instructions
  with `enabled=false`.
- Added CLI tests for review summaries, sender-domain overrides, intent
  recording after completed preservation, and controlled rejection of unknown
  records.
- Updated README, development docs, closeout notes, and current-state audit.
- Validation: `python -m unittest discover -s tests` passed with 165 tests and
  17 expected skips.
