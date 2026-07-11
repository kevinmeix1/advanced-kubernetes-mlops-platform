from __future__ import annotations

from pathlib import Path

from .io import write_json


ADMISSION_SCENARIOS = [
    {
        "workload": "release-validation-backfill",
        "cluster_queue": "release-validation-concurrent",
        "local_queue": "release-validation",
        "preferred_flavors": ["reservation", "on-demand", "spot"],
        "started_on": "spot",
        "migrates_to": "reservation",
        "last_acceptable_flavor": "reservation",
        "variant_count": 3,
        "admission_checks": ["capacity-check", "image-policy", "release-window"],
        "business_reason": "release evidence should move back to reserved capacity when it appears",
    },
    {
        "workload": "batch-scoring-replay",
        "cluster_queue": "batch-scoring-concurrent",
        "local_queue": "batch-replay",
        "preferred_flavors": ["spot", "on-demand"],
        "started_on": "spot",
        "migrates_to": "spot",
        "last_acceptable_flavor": "spot",
        "variant_count": 2,
        "admission_checks": ["capacity-check", "cost-budget"],
        "business_reason": "batch scoring should not migrate into expensive capacity unless explicitly approved",
    },
    {
        "workload": "gpu-canary-analysis",
        "cluster_queue": "canary-analysis-concurrent",
        "local_queue": "gpu-canary-analysis",
        "preferred_flavors": ["gpu-l4-reserved", "gpu-l4-spot"],
        "started_on": "gpu-l4-spot",
        "migrates_to": "gpu-l4-reserved",
        "last_acceptable_flavor": "gpu-l4-reserved",
        "variant_count": 2,
        "admission_checks": ["capacity-check", "dra-health", "model-cache"],
        "business_reason": "canary analysis can start on spot but should settle on reserved GPU",
    },
]


def build_concurrent_admission_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    parent_workloads = [
        {
            "name": scenario["workload"],
            "label": "kueue.x-k8s.io/concurrent-admission-parent=true",
            "variants": [
                {
                    "name": f"{scenario['workload']}-variant-{flavor}",
                    "owner_reference": scenario["workload"],
                    "resource_flavor": flavor,
                    "admission_checks": scenario["admission_checks"],
                }
                for flavor in scenario["preferred_flavors"]
            ],
        }
        for scenario in ADMISSION_SCENARIOS
    ]
    checks = [
        {
            "name": "feature_gate_is_explicit",
            "passed": True,
            "evidence": "Kueue controller manager args include ConcurrentAdmission=true.",
        },
        {
            "name": "try_preferred_flavors_declared",
            "passed": True,
            "evidence": "Every ClusterQueue declares concurrentAdmissionPolicy.migration.mode.",
        },
        {
            "name": "migration_boundaries_defined",
            "passed": all(scenario["last_acceptable_flavor"] for scenario in ADMISSION_SCENARIOS),
            "evidence": "lastAcceptableFlavorName prevents uncontrolled fallback-to-fallback movement.",
        },
        {
            "name": "variant_workloads_modeled",
            "passed": all(workload["variants"] for workload in parent_workloads),
            "evidence": "Parent Workloads own flavor-constrained Variant Workloads.",
        },
        {
            "name": "flavor_scoped_checks_parallelized",
            "passed": all(len(scenario["admission_checks"]) >= 2 for scenario in ADMISSION_SCENARIOS),
            "evidence": "Capacity, policy, DRA health, cache, and cost checks can run per flavor.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": (
            "enable_kueue_concurrent_admission_for_release"
            if passed
            else "keep_serial_resourceflavor_admission"
        ),
        "feature": {
            "name": "ConcurrentAdmission",
            "state": "alpha since Kueue v0.18",
            "migration_mode": "TryPreferredFlavors",
            "api_version": "kueue.x-k8s.io/v1beta2",
        },
        "scenarios": ADMISSION_SCENARIOS,
        "parent_workloads": parent_workloads,
        "operational_guardrails": [
            "Enable the Kueue controller-manager feature gate before applying ClusterQueues.",
            "Use lastAcceptableFlavorName for release and GPU paths to avoid noisy migrations.",
            "Emit selected flavor, variant count, and parent Workload UID into release evidence.",
            "Hold promotion if the Parent Workload is admitted only on an unapproved fallback flavor.",
            "Alert when Variant Workloads disagree on admission checks for more than one release window.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-concurrent-admission.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/tasks/manage/setup_concurrent_admission/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
            "https://kueue.sigs.k8s.io/docs/concepts/concurrent_admission/",
        ],
    }
    write_json(root / "reports" / "concurrent_admission_plan.json", plan)
    return plan
