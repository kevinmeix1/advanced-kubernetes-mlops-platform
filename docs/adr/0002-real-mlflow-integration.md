# ADR 0002: Real MLflow Integration Boundary

- Status: accepted
- Date: 2026-07-10

## Context

The project used files shaped like MLflow runs and registry entries. That kept
the demo fast, but it did not prove compatibility with a current MLflow tracking
server, SQL registry, model packaging, aliases, or artifact loading.

Making MLflow a mandatory dependency would turn a short local review into a
large environment install and would couple all architecture-report tests to an
external framework.

## Decision

Keep two explicit execution modes:

1. A dependency-light local lifecycle for deterministic domain behavior.
2. An isolated MLflow 3.14 integration contract installed from an exact
   constraints file and exercised against both direct SQLite and an HTTP server.

Use model aliases and version tags rather than deprecated model stages. Package
the predictor with model-from-code, an explicit signature, a model-config
artifact, and dataset-linked metrics. Treat application-version reuse with
different evidence as a conflict.

The Compose server uses a finite database migration job, one MLflow worker,
SQLite metadata, proxied local artifacts, and a named volume. This is an
integration environment, not the production topology.

## Consequences

- Reviewers can run the fast path without MLflow.
- CI proves current MLflow API behavior and a real HTTP boundary.
- Registry, alias, signature, lineage, loading, and rollback claims have direct
  evidence.
- CI is slower and the MLflow job has a larger dependency surface.
- Alias promotion is not atomic across multiple API calls and requires a
  serialized release controller in production.
- Production still requires PostgreSQL, object storage, authentication, TLS,
  backup, and a live KServe reconciliation loop.
