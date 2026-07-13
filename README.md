# Email Vault POC

Email Vault is a portfolio-quality proof of concept for preserving the accessible
snapshot of one opened Gmail thread. This repository currently contains the P0/P1
foundation only: product scope, architecture notes, canonical contracts,
synthetic fixtures, and invariant tests.

No Gmail mutation, production OAuth, cloud storage, AI, deletion, or deployment
behavior is implemented in this phase.

## Quick Start

```powershell
python -m unittest discover -s tests
```

The foundational contract tests use only the Python standard library. To run the
P2 FastAPI skeleton tests and local API, install the optional API/test
dependencies:

```powershell
python -m pip install -e ".[api,test]"
python -m unittest discover -s tests
uvicorn services.api.app.main:app --reload
```
