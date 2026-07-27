# Development

This document explains how to run the current Email Vault P2 build locally.

## Requirements

- Python 3.12 or newer.
- No real Gmail credentials are needed for default local development.
- No real email data should be added to the repository.

## Install

```powershell
python -m pip install -e ".[api,test]"
```

The project currently uses optional dependencies for the API and tests:
FastAPI, Pydantic v2, Uvicorn, google-auth, httpx, and pytest.

Renderer work uses a separate optional dependency so standard tests stay light:

```powershell
python -m pip install -e ".[renderer]"
python -m playwright install chromium
```

The renderer optional dependency is not required for the standard-library unit
suite. It is needed before running browser-backed PDF rendering locally.

## Renderer Smoke Test

The browser-backed renderer smoke test is opt-in because it needs the Playwright
package and a local Chromium runtime.

```powershell
$env:EMAIL_VAULT_RUN_RENDERER_SMOKE = "1"
python -m unittest tests.test_playwright_renderer_smoke
Remove-Item Env:\EMAIL_VAULT_RUN_RENDERER_SMOKE
```

Without `EMAIL_VAULT_RUN_RENDERER_SMOKE=1`, the smoke test skips cleanly during
normal test runs.

## Configure

Copy `.env.example` only when you need a local environment file. Keep real
secrets out of Git.

Local authentication defaults to the synthetic verifier:

```text
EMAIL_VAULT_IDENTITY_VERIFIER=synthetic
Authorization: Bearer synthetic-valid-token
```

Production-like identity verification can be enabled only after installing the
API optional dependencies and configuring a real Google OAuth client ID:

```text
EMAIL_VAULT_IDENTITY_VERIFIER=google
GOOGLE_OAUTH_CLIENT_ID=<your-google-oauth-client-id>
```

Do not commit real OAuth client IDs, tokens, or exported email data. The test
suite uses fake verifier functions and does not call Google.

Add-on request signing is off by default for local development. Configure a
private shared secret only when testing the add-on-to-backend boundary:

```text
EMAIL_VAULT_ADDON_SIGNING_SECRET=<private-shared-secret>
EMAIL_VAULT_ADDON_SIGNATURE_MAX_AGE_SECONDS=300
```

The default local database URL is:

```text
sqlite:///./email_vault.db
```

## Bootstrap the Local Database

```powershell
python -m services.api.app.cli init-db
```

The command creates the SQLite schema if it does not already exist. It is safe to
run more than once.

## Run Local Preserve Mode

The first hands-on local interface is a CLI command. It accepts one
`ArchiveThreadRequest` JSON file, a user-selected export root, and optional
trusted attachment-byte mappings. It writes a verified local export package and
prints the generated package path plus verification summary.

```powershell
python -m services.api.app.cli preserve-local --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --json
```

For requests with attachments, pass trusted bytes for each attachment:

```powershell
python -m services.api.app.cli preserve-local --request path/to/request.json --export-root E:\EmailVault --attachment-content msg-123:att-123=path\to\attachment.pdf
```

The attachment descriptor in the request must match the supplied byte size and
SHA-256 checksum. If bytes are missing or mismatched, the CLI rejects the package
and removes partial output.

## Run Local Clean Inbox Review

Clean Inbox review previews what Email Vault would do after verified export. It
does not write export packages, label Gmail, mark Gmail read, archive Gmail, or
delete Gmail messages.

```powershell
python -m services.api.app.cli clean-inbox-review --request tests/fixtures/emails/newsletter_digest.json --request tests/fixtures/emails/bank_notice.json --request tests/fixtures/emails/unknown_message.json --mark-read --json
```

The command prints batch counts plus one item per thread: category,
sender-domain route, planned export path, planned Gmail action, classifier
evidence, and whether the item requires review.

Sender-domain routing can be overridden per thread for local batching tests:

```powershell
python -m services.api.app.cli clean-inbox-review --request tests/fixtures/emails/newsletter_digest.json --sender-domain-override gmail-thread-newsletter-001=daily.news.example.com --json
```

## Record Local Clean Inbox Intent

After `preserve-local` returns a completed record id, Clean Inbox intent can be
recorded as an audit marker:

```powershell
python -m services.api.app.cli record-clean-inbox-intent --record-id <record-id-from-preserve-local> --mark-read --json
```

The command returns Gmail finalization instructions with `enabled=false`. It is
safe for the public POC because it records the user's intended cleanup choice
without mutating Gmail.

## Run The Local Batch Workflow

The batch command is the tightest synthetic demo path. It preserves each request
into the selected export root, produces one Clean Inbox review summary, and can
record intent only for lower-risk items that do not require review.

```powershell
python -m services.api.app.cli local-batch --request tests/fixtures/emails/newsletter_digest.json --request tests/fixtures/emails/bank_notice.json --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --mark-read --record-approvable-intents --report-markdown .local/demo-report.md --json
```

The command is still local-only and mutation-disabled. Bank, human,
attachment-heavy, unknown, and other review-required categories are preserved
and reported, but they do not receive intent records from
`--record-approvable-intents`. The optional Markdown report is public-safe for
synthetic demos because it omits absolute local package paths.

## Run Tests

```powershell
python -m pytest
python -m unittest discover -s tests
```

Both commands are expected to pass. A FastAPI/Starlette test-client deprecation
warning may appear; it does not currently indicate a project failure.

## Continuous Integration

GitHub Actions runs the stable test suite on push to `main` and on pull
requests:

```powershell
python -m unittest discover -s tests
```

The CI job installs `.[api,test]` so API tests run, but it does not install the
renderer optional dependency or Chromium. The browser-backed renderer smoke test
remains opt-in with `EMAIL_VAULT_RUN_RENDERER_SMOKE=1`. CI also builds the API
Docker image to catch runtime packaging drift.

## Gmail Add-on Shell

The preview-only Workspace Add-on shell lives in:

```text
services/gmail_addon/
```

It includes an Apps Script manifest, Gmail contextual card code, and local tests.
The shell can collect archive preferences and can call the backend when script
properties are configured. It still does not mutate Gmail.

Apps Script deployment properties for backend calls:

```text
EMAIL_VAULT_BACKEND_URL=<https-api-origin>
EMAIL_VAULT_ADDON_SIGNING_SECRET=<private-shared-secret>
```

## Run the API

```powershell
python -m uvicorn services.api.app.main:app --reload
```

Current local authentication uses the synthetic verifier unless
`EMAIL_VAULT_IDENTITY_VERIFIER=google` is set:

```text
Authorization: Bearer synthetic-valid-token
```

This token is not production authentication. In Google verifier mode, the bearer
credential must be a Google ID token for the configured OAuth client ID.

## Current Limits

The archive route can render the generated PDF path, generate metadata and
manifest JSON artifacts, copy permitted attachments when a trusted content
provider supplies bytes, stage and verify local storage, and record a completed
backend revision. The local Preserve Mode CLI can write portable export packages
to a selected folder. The local Clean Inbox review and intent commands can
preview cleanup and record post-preservation intent. The local batch command
chains those pieces for synthetic demos and can write a Markdown report without
absolute package paths. None of these paths labels Gmail, marks messages read,
archives Gmail, trashes Gmail, or deletes Gmail messages.
