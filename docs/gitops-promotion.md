# GitOps Promotion

This project includes an Argo CD and Argo Rollouts example for auditable environment promotion. The local report documents the sync waves, release gates, approvals, and rollback commands; the manifest shows how those decisions can be represented declaratively.

Run:

```bash
make gitops-plan
```

The report is written to `.local/reports/gitops_plan.json`.

## Design

- Use a separate config repository pattern for production manifests and immutable image digests.
- Apply policies, network boundaries, quotas, and autoscalers before workloads.
- Run model, policy, topology, and smoke-test checks as pre-sync or post-sync evidence.
- Keep prod sync manual even if dev and staging use automated sync and self-healing.
- Use Argo Rollouts analysis templates for latency and error-rate canary gates.

## References

Argo CD sync hooks and waves order resources before, during, and after sync. Automated sync can prune and self-heal live drift. Argo Rollouts AnalysisTemplates connect canary promotion to metrics and can abort unsafe rollouts.
