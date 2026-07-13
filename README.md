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

The current code uses only the Python standard library so the foundational tests
can run without installing packages. Later API phases are expected to introduce
FastAPI and Pydantic v2.

