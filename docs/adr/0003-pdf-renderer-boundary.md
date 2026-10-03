# ADR 0003: PDF Renderer Boundary

## Status

Accepted for P3 planning.

## Context

Email Vault must render a readable PDF from a sanitized, renderer-safe thread
snapshot. Email HTML can contain hostile markup, tracking pixels, remote assets,
and layout tricks. The renderer therefore needs stronger isolation than ordinary
HTML-to-PDF convenience calls.

The master build prompt says that the renderer decision must be documented
before implementation. It also prefers Playwright/Chromium in Docker with
JavaScript disabled and network interception blocking every request when no
existing renderer dictates otherwise.

## Decision

The POC PDF renderer will be designed around Playwright/Chromium, but renderer
implementation remains deferred until after this ADR.

Renderer requirements:

- consume `RendererSafeThreadSnapshot`, not raw email HTML;
- render only sanitized message content plus server-generated metadata;
- disable JavaScript for rendered email content;
- block every network request, including images, fonts, stylesheets, scripts,
  frames, beacons, and fetch/XHR calls;
- use a temporary workspace for generated PDF, metadata JSON, manifest JSON, and
  checksums;
- clean the temporary workspace on success and every controlled failure path;
- return generated artifacts to the storage boundary without marking any
  revision completed;
- never trigger Gmail finalization.

The renderer may use local, repository-owned styles for stable readable output.
It must not fetch remote styles, images, fonts, or scripts.

## Consequences

- PDF visual fidelity is subordinate to safety and repeatability.
- Exact email-client rendering is not promised.
- Docker or documented runtime setup will be needed before a public demo can
  reliably run Chromium.
- Tests must prove JavaScript is not executed, remote requests are blocked, and
  temporary files are cleaned before renderer/storage integration is considered
  public-ready.
- Storage verification remains the transaction boundary. Rendering a PDF alone
  is not a completed archive.
