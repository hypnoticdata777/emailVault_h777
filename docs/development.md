# Development

This document explains how to run the current Email Vault P2 build locally.

## Requirements

- Python 3.12 or newer.
- No real Gmail credentials are needed for the current phase.
- No real email data should be added to the repository.

## Install

```powershell
python -m pip install -e ".[api,test]"
```

The project currently uses optional dependencies for the API and tests:
FastAPI, Pydantic v2, Uvicorn, httpx, and pytest.

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

## Run the API

```powershell
python -m uvicorn services.api.app.main:app --reload
```

Current local authentication uses a synthetic token only:

```text
Authorization: Bearer synthetic-valid-token
```

This is not production authentication. Real Google ID-token verification belongs
to a later phase.

## Current Limits

The archive route validates input, checks duplicate state, and returns controlled
responses. The renderer scaffold and Playwright adapter boundary exist, but the
archive route does not yet render PDFs, stage storage, write completed
revisions, label Gmail, mark messages read, or archive Gmail.
