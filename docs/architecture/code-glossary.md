# Code Glossary

This is a practical map of the repository. Start with the files in the first
table when explaining the project; the remaining sections cover the important
boundaries behind them.

## Files to know first

| File | Practical meaning |
| --- | --- |
| `services/api/app/main.py` | FastAPI composition root. Creates the app and includes routers. |
| `services/api/app/api/routes.py` | HTTP contract for health, preservation, and finalization. |
| `services/api/app/api/schemas.py` | Pydantic transport validation and response conversion. |
| `services/api/app/domain/contracts.py` | Framework-independent domain models, statuses, errors, and fingerprints. |
| `services/api/app/services/archive.py` | Application coordinator for preserve, verify, complete, and finalization boundaries. |
| `services/api/app/cli.py` | Local commands and synthetic demo orchestration. |
| `services/api/app/repositories/sqlite.py` | Local persistence for revisions and audit events. |
| `services/gmail_addon/Code.gs` | Gmail Workspace Add-on shell and signed backend calls. |
| `tests/fixtures/emails/*.json` | Synthetic request fixtures used by demos and tests. |
| `.github/workflows/ci.yml` | Python 3.12 test and Docker build verification. |

## Domain language

- **ThreadSnapshot:** the conversation-level archive input. It contains one or
  more `MessageSnapshot` values.
- **MessageSnapshot:** one message’s sender, recipients, headers, bodies, and
  attachment descriptors.
- **ArchiveThreadRequest:** thread plus preferences, client context, and
  optional trusted attachment provider data.
- **ArchiveRecordReference:** stable record ID, Gmail thread ID, and snapshot
  fingerprint for a stored revision.
- **ArchiveState:** lifecycle marker such as `VERIFIED`, `COMPLETED`, or
  `GMAIL_FINALIZATION_PENDING`.
- **ArchiveResult:** the boundary response returned by the coordinator and
  converted to an API response by `api/schemas.py`.

## Core functions and classes

- `ArchiveCoordinator.preserve` runs the rendered-artifact preservation path.
- `ArchiveCoordinator.preserve_export_package_with_details` runs the local
  Preserve Mode package path used by the CLI.
- `RevisionPlanner.plan` prevents the same owner/thread fingerprint from being
  treated as a new export without an explicit new revision decision.
- `classify_thread` applies deterministic evidence rules for newsletter,
  automated, bank/financial, human, attachment-heavy, and unknown mail.
- `plan_export_route` selects a safe domain-first or category-first folder.
- `write_export_package` writes and verifies `.eml`, metadata, text,
  attachments, and manifest artifacts.
- `prepare_renderer_safe_thread` ensures renderers see sanitized content and a
  plain-text fallback.
- `assert_transition_allowed` is the guardrail that keeps lifecycle changes in
  the allowed order.
- `sign_request` and `AddonRequestSignatureVerifier` authenticate the add-on
  request boundary when a signing secret is configured.

## Routes

- `GET /health` is a liveness check.
- `GET /demo` is a synthetic, read-only review surface.
- `GET /login` and its POST actions provide local access selection.
- `GET /admin` is an owner console shell, not a live Gmail inbox.
- `POST /archive/thread` preserves the backend copy and never mutates Gmail.
- `POST /archive/thread/gmail-finalization` records an explicit handoff after
  completion.
- `POST /archive/thread/gmail-finalization/callback` records the later result.
- `GET /oauth/google/callback` completes the configured private OAuth exchange
  and encrypted local token storage path.

## Patterns worth recognizing

- **Ports and adapters:** `Protocol` types for repositories, storage, PDF
  rendering, identity, and attachment content keep the coordinator testable.
- **Boundary-first security:** identity, HMAC signing, path validation, HTML
  sanitization, and checksum verification happen at explicit seams.
- **Immutable-ish value objects:** frozen dataclasses and enum states make the
  workflow easier to reason about and serialize.
- **Dry run before side effects:** `plan_export_dry_run` produces reviewable
  category, route, and planned-action output before a cleanup intent is stored.
- **Audit trail as state machine:** SQLite stores revision ownership and ordered
  audit events; `domain/state.py` rejects invalid transitions.

## Where tests explain behavior

- `tests/test_contracts.py` — contract validation and canonical behavior.
- `tests/test_revision_planner.py` — duplicate and updated-thread planning.
- `tests/test_sanitization.py` and `tests/test_renderer_safe_snapshot.py` —
  hostile HTML and renderer input safety.
- `tests/test_export_classification.py`, `test_export_routing.py`, and
  `test_export_dry_run.py` — classification and operator review.
- `tests/test_export_writer.py`, `test_export_package.py`, and
  `test_artifact_manifest.py` — package contents and checksums.
- `tests/test_archive_service.py` and `tests/test_api.py` — lifecycle and HTTP
  behavior.
- `tests/test_gmail_addon_shell.py` and `test_request_signing.py` — add-on
  boundaries and signed requests.
