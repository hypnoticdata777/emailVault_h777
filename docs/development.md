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
remains opt-in with `EMAIL_VAULT_RUN_RENDERER_SMOKE=1`.

## Gmail Add-on Shell

The preview-only Workspace Add-on shell lives in:

```text
services/gmail_addon/
```

It includes an Apps Script manifest, Gmail contextual card code, and local tests.
The shell can collect archive preferences, but it does not call the backend or
mutate Gmail yet.

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

The archive route validates input, checks duplicate state, and returns controlled
responses. The renderer scaffold and Playwright adapter boundary exist, but the
archive route does not yet render PDFs, stage storage, write completed
revisions, label Gmail, mark messages read, or archive Gmail.
