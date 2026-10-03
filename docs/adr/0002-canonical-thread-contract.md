# ADR 0002: Canonical Thread Contract

## Status

Accepted for P0/P1.

## Context

The add-on and backend need a shared representation of the accessible Gmail
thread snapshot. The contract must be deterministic enough for duplicate
fingerprinting and strict enough to reject unsupported or unsafe payloads.

## Decision

P1 defines canonical request, snapshot, message, participant, body, attachment,
preference, response, state, and error concepts in Python. The current
implementation uses dataclasses and explicit validators because this environment
does not have Pydantic installed. When FastAPI is introduced, these contracts
should move to Pydantic v2 models with equivalent validation behavior.

## Consequences

- The foundation runs without dependency installation.
- Pydantic migration must preserve field names and invariant behavior.
- Fixture JSON is the cross-boundary format for early contract tests.

