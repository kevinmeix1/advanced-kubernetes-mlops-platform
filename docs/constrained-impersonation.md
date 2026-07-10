# Constrained Impersonation

`make constrained-impersonation` writes `.local/reports/constrained_impersonation_plan.json`.

## What It Shows

- Kubernetes v1.36 `ConstrainedImpersonation` beta behavior.
- Separate authorization for the impersonated service account identity and the actions performed while impersonating.
- Release support and rollback workflows that can inspect or patch only the resources they need.
- Audit expectations for `authenticationMetadata.impersonationConstraint`.
- Alerts for legacy broad `impersonate` grants that bypass least-privilege intent.

## Production Notes

The release controller and debugging tools should not inherit every permission
held by a release identity. Constrained impersonation lets the platform grant
`impersonate:serviceaccount` for the exact target service account and
`impersonate-on:serviceaccount:<verb>` only for specific resources.

This is useful for break-glass release support, rollback status updates, and
debugging without giving support tools create/delete access to model workloads.

References:

- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/
