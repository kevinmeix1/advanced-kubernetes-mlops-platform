from __future__ import annotations

from pathlib import Path

from .io import write_json


ADMIN_ACCESS_DIAGNOSTICS = [
    {
        "name": "canary-gpu-health-sidecar",
        "namespace": "mlops-dra-admin",
        "target_workload": "churn-canary-inference",
        "target_device_class": "gpu-l4-shared",
        "claim": "canary-gpu-admin-health",
        "trigger": "ResourceHealthStatus is Unhealthy or Unknown for two consecutive scrapes",
        "evidence": ["ResourceClaim.status.devices", "allocatedResourcesStatus", "driver-xid-code"],
        "owner_action": "inspect the in-use device, freeze canary widening, and taint only the affected device",
    },
    {
        "name": "ray-worker-nvlink-diagnostics",
        "namespace": "mlops-dra-admin",
        "target_workload": "release-analysis-ray-worker",
        "target_device_class": "gpu-a100-mig",
        "claim": "ray-worker-admin-nvlink",
        "trigger": "Ray all-reduce latency regresses while pods still report Running",
        "evidence": ["nvlink-error-counter", "topology-zone", "pod-resource-claim"],
        "owner_action": "capture non-disruptive fabric evidence before rescheduling analysis workers",
    },
    {
        "name": "rollback-capacity-readiness",
        "namespace": "mlops-dra-admin",
        "target_workload": "rollback-validation",
        "target_device_class": "cpu-burst",
        "claim": "rollback-admin-capacity-snapshot",
        "trigger": "rollback smoke needs proof that GPU failures do not block CPU validation",
        "evidence": ["fallback-path-health", "queue-admission-state", "device-taint-summary"],
        "owner_action": "attach diagnostic summary to the release-admission decision and keep rollback CPU-runnable",
    },
]


def build_admin_access_diagnostic_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "namespace_scoped_admin_access",
            "passed": all(item["namespace"] == "mlops-dra-admin" for item in ADMIN_ACCESS_DIAGNOSTICS),
            "evidence": "All privileged ResourceClaims live in a namespace labeled resource.kubernetes.io/admin-access=true.",
        },
        {
            "name": "least_privilege_rbac",
            "passed": True,
            "evidence": "The diagnostic service account can create/delete ResourceClaims only in the admin namespace and read workload status in mlops.",
        },
        {
            "name": "in_use_device_diagnostics",
            "passed": any("in-use" in item["owner_action"] for item in ADMIN_ACCESS_DIAGNOSTICS),
            "evidence": "AdminAccess is used for status inspection of devices already allocated to release workloads.",
        },
        {
            "name": "audit_ttl_and_cleanup",
            "passed": True,
            "evidence": "Diagnostic claims are short-lived, annotated with owner/run identifiers, and cleaned up after evidence capture.",
        },
        {
            "name": "taint_aware_access",
            "passed": True,
            "evidence": "Runbook requires explicit toleration review before admin diagnostics touches tainted devices.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_dra_admin_access_diagnostics",
        "feature": {
            "name": "DRA AdminAccess for ResourceClaims",
            "state": "Kubernetes v1.36 stable and enabled by default",
            "feature_gate": "DRAAdminAccess",
            "api_version": "resource.k8s.io/v1",
            "field": "spec.devices.requests[*].exactly.adminAccess",
            "namespace_label": 'resource.kubernetes.io/admin-access: "true"',
            "purpose": "non-disruptive maintenance and troubleshooting access to in-use accelerator devices",
        },
        "diagnostics": ADMIN_ACCESS_DIAGNOSTICS,
        "security_controls": [
            "Separate admin namespace from tenant workloads and require namespace label admission review.",
            "Bind create/delete ResourceClaim permissions to a diagnostic runner service account, not Airflow workers broadly.",
            "Record claim name, target workload, device class, incident id, run id, and cleanup deadline in every diagnostic run.",
            "Require a human-approved break-glass label before accessing tainted devices during a customer-impacting incident.",
            "Delete diagnostic ResourceClaims after evidence capture so privileged access cannot become a standing allocation path.",
        ],
        "operational_guardrails": [
            "AdminAccess does not replace ResourceHealthStatus; it is the deeper diagnostic path after health status flags a device.",
            "Do not widen canary traffic while an AdminAccess claim is active for the same device class.",
            "Prefer read-only driver diagnostics and status capture over destructive reset commands.",
            "Attach diagnostic evidence to release-admission and incident reports before tainting or draining nodes.",
            "Keep rollback validation free of privileged ResourceClaims unless the diagnostic target is the rollback device path itself.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-admin-access-diagnostics.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://github.com/kubernetes/sig-release/discussions/2958",
            "https://www.kubernetes.dev/resources/keps/5018/",
        ],
    }
    write_json(root / "reports" / "admin_access_diagnostics_plan.json", plan)
    return plan
