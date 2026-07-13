# ADR 0001: POC Scope and Transaction Boundary

## Status

Accepted for P0/P1.

## Context

Email Vault must preserve an accessible Gmail thread snapshot without risking
message loss or premature mailbox mutation. The key product promise is that
Gmail changes happen only after verified durable storage.

## Decision

The backend storage verification result is the transaction boundary. Any label,
mark-read, or archive instruction can be returned only after artifacts are staged
and verified. Failure before verification must leave Gmail unchanged.

P0/P1 will not implement Gmail mutation behavior. It may define state transitions
and response concepts that make later finalization explicit.

## Consequences

- The add-on must wait for backend confirmation before changing Gmail state.
- State transitions must reject finalization before `VERIFIED`.
- Later phases need durable audit/revision persistence before renderer and
  storage work can be considered complete.

