# Runtime Security

`make runtime-security` writes `.local/reports/runtime_security_plan.json`.

## What It Shows

- Kubernetes v1.36 user namespaces GA readiness with `pod.spec.hostUsers: false`.
- Runtime prerequisites for user namespaces: Linux 6.3+, idmap-capable filesystems, containerd 2.0+ or CRI-O 1.25+, and runc 1.2+ or crun 1.13+.
- Kubernetes v1.36 fine-grained kubelet authorization (`KubeletFineGrainedAuthz`) using `nodes/metrics`, `nodes/stats`, and `nodes/pods`.
- A policy example that blocks new monitoring roles from granting broad `nodes/proxy`.
- Reduced blast radius for release training, telemetry, and rollback smoke workloads.

## Production Notes

User namespaces let a workload run as root inside the container while mapping that process to an unprivileged host UID. That is useful for ML images that still need package or model-cache setup steps but should not become host-root if compromised.

Fine-grained kubelet authorization removes the old pattern where monitoring agents needed `nodes/proxy` just to read kubelet metrics. The manifest grants only the kubelet subresources required for release telemetry and leaves privileged kubelet access as an audited break-glass path.

## Senior Review Angle

This shows that the platform handles runtime isolation and kubelet observability access as part of the MLOps control plane. It links release jobs, telemetry, rollback smoke, RBAC, admission policy, and node-pool readiness instead of treating Kubernetes security as a README afterthought.

References:

- https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/
- https://kubernetes.io/docs/tasks/configure-pod-container/user-namespaces/
- https://kubernetes.io/blog/2026/04/24/kubernetes-v1-36-fine-grained-kubelet-authorization-ga/
- https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/
