# ADR-0001: Modular Monolith

## Status

Accepted

## Context

The hackathon scope is narrow, local-first, and audit-heavy. A distributed architecture would add operational overhead without improving the core decision flow.

## Decision

Adopt a modular monolith with clear package boundaries for domain logic, orchestration, adapters, model integration, audit, storage, and UI.

## Consequences

- Faster delivery and lower setup cost
- Easier end-to-end debugging
- Tighter control of deterministic rules and audit payloads
- Future extraction remains possible because boundaries are explicit

