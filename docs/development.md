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
responses. It does not render PDFs, stage storage, write completed revisions,
label Gmail, mark messages read, or archive Gmail.

