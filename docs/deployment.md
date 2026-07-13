# Deployment Runtime

Email Vault now has a first Docker runtime boundary for the FastAPI API.

Current files:

- `Dockerfile` builds a Python 3.12 slim image for `services.api.app.main:app`
  with API, renderer, and Chromium runtime dependencies.
- `.dockerignore` keeps local databases, secrets, tests, docs, and the
  Apps Script add-on shell out of the API image.

Local image build:

```powershell
docker build -t email-vault-api:local .
```

Initialize the SQLite database inside a mounted data directory:

```powershell
docker run --rm -v ${PWD}/.local/runtime-data:/data email-vault-api:local `
  python -m services.api.app.cli init-db
```

Run the API:

```powershell
docker run --rm -p 8000:8000 -v ${PWD}/.local/runtime-data:/data email-vault-api:local
```

Default runtime paths:

- `EMAIL_VAULT_STORAGE_ROOT=/data/email-vault-storage`
- `DATABASE_URL=sqlite:////data/email_vault.db`

Public-demo requirements still open:

- configure `EMAIL_VAULT_IDENTITY_VERIFIER=google`;
- configure a real `GOOGLE_OAUTH_CLIENT_ID` outside Git;
- choose an HTTPS deployment target;
- decide whether SQLite is acceptable for the demo or replace it with a managed
  database;
- wire the add-on to the archive route only after request signing, deployment,
  and live OAuth settings are ready.
