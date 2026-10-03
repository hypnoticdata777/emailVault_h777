# Email Vault: Site and System Walkthrough

This guide explains what a person can do with the project today and how each
step is connected to the code. “Site” includes the local web demo and admin
shell; the core product workflow also has a CLI and a Gmail Workspace Add-on
entry point.

## The one-minute story

Email Vault preserves a Gmail thread outside Gmail before any cleanup is
considered. A request is authenticated and validated, the thread is classified
and routed, unsafe HTML is sanitized, export artifacts are written and checked
with SHA-256, and the result is recorded in SQLite. Only after completion can a
separate finalization boundary describe a future Gmail-side action. In the
current POC, that mutation is deliberately not executed.

## Entry points

| Entry point | What it is for | Code |
| --- | --- | --- |
| `GET /demo` | Read-only synthetic review queue and summary | `services/api/app/api/demo.py` |
| `GET /login`, `POST /login/demo` | Local access split for demo and owner shell | `services/api/app/api/web.py` |
| `GET /admin` | Owner-only shell showing OAuth and token-store readiness | `services/api/app/api/web.py` |
| `POST /archive/thread` | Backend preservation route | `services/api/app/api/routes.py` |
| `preserve-local` | Preserve one request fixture into a local package | `services/api/app/cli.py` |
| `local-batch` / `synthetic-demo` | Run the public-safe batch workflow | `services/api/app/cli.py` |
| Gmail contextual card | Preview a selected thread and submit preferences | `services/gmail_addon/Code.gs` |

`services/api/app/main.py:create_app` assembles the FastAPI app by including the
API, demo, and web routers.

## Flow A: public local demo

1. Start the API with Uvicorn and open `/demo`.
2. `api/demo.py` loads the three canonical fixtures: newsletter, bank/financial,
   and unknown mail.
3. `plan_export_dry_run` classifies each thread, calculates a sender-domain
   route, and marks higher-risk items for review.
4. The HTML response shows counts, planned actions, and the CLI handoff. It is
   review-only: it does not write export files or mutate Gmail.

This is the safest surface for portfolio review because its data comes from
`tests/fixtures/emails` and the limitation is visible in the UI.

## Flow B: local Preserve Mode

The CLI reads an `ArchiveThreadRequest` JSON fixture, creates a synthetic
verified owner, and calls `ArchiveCoordinator.preserve_export_package_with_details`
in `services/api/app/services/archive.py`.

The coordinator then:

1. validates identity and the request;
2. asks `RevisionPlanner` whether this is a duplicate, new revision, or updated
   thread;
3. classifies the thread with `export_classification.py`;
4. selects a safe folder route with `export_routing.py`;
5. plans package artifacts in `domain/export_package.py`;
6. writes `.eml`, metadata JSON, normalized text, optional trusted attachments,
   and a manifest through `export_writer.py`;
7. verifies file size and checksums;
8. persists `RENDERED`, `STAGED`, `VERIFIED`, and `COMPLETED` audit events in
   the configured SQLite repository.

The result includes a package path and verification summary. Gmail is unchanged.

## Flow C: Gmail Add-on request

`services/gmail_addon/Code.gs` builds a contextual card from the selected
thread. The operator chooses a category and optional mark-read/archive intent.
The shell reads the thread preview, gathers trusted attachment bytes when
available, signs the request with HMAC, and calls `/archive/thread`.

The API route uses dependency boundaries for identity, signatures, repository,
renderer, storage, and attachments. It delegates preservation to
`ArchiveCoordinator.preserve`. The route can return `PRESERVED` or `DUPLICATE`,
but its finalization instructions remain disabled.

If a later step calls `/archive/thread/gmail-finalization`, the coordinator only
allows it after `COMPLETED` (or recorded Clean Inbox intent). The callback route
records success or failure after `GMAIL_FINALIZATION_PENDING`. The state rules
live in `domain/state.py`.

## Flow D: private owner and OAuth readiness

`/login` separates demo access from the local owner console. The admin shell is
not a live mailbox UI yet. It reports whether Google OAuth configuration and the
encrypted local token store are ready. `api/web.py` signs OAuth state, checks
the admin session, exchanges the code through `auth/oauth_exchange.py`, and
writes token material through `auth/token_storage.py`.

The next private implementation step is read-only Gmail listing/import. The
current repository does not claim live Gmail sync or Gmail mutation.

## What a reviewer should notice

- Preservation and mutation are separate routes and separate state transitions.
- Input contracts are defined in `domain/contracts.py` and API schemas in
  `api/schemas.py`.
- Unsafe HTML is handled before rendering by `services/sanitization` and
  `services/rendering/snapshot.py`.
- Storage is a replaceable protocol, with a local filesystem implementation in
  `services/storage/provider.py`.
- The test suite covers boundary behavior instead of only happy-path HTTP calls.
