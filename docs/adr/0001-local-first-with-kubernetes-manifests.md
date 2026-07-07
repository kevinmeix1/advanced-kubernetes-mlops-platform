# ADR 0001: Local-First Demo With Kubernetes Manifests

## Status

Accepted

## Context

Portfolio reviewers should be able to run the project quickly without installing a full Kubernetes stack. At the same time, the project should demonstrate the production architecture expected from an advanced MLOps platform: orchestration, model registry, serving, monitoring, and rollback.

## Decision

The default path runs locally with the Python standard library and writes concrete artifacts under `.local/`. The repo also includes Airflow, Metaflow, KServe, Prometheus, and Grafana scaffolding that maps each local artifact to a production service.

## Consequences

Benefits:

- `make demo` is reliable and fast.
- Tests run without external services.
- The local artifact structure is inspectable.
- Production intent is still visible through manifests and docs.

Trade-offs:

- Local serving is a KServe simulation, not an active Kubernetes deployment.
- MLflow is represented through registry-compatible metadata files unless the optional stack is started.
- Production security, autoscaling, and remote artifact storage are documented rather than fully provisioned.

