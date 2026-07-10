from __future__ import annotations

from pathlib import Path

from .io import write_json


DELEGATIONS = [
    {
        "name": "release-debugger-read-champion",
        "namespace": "mlops",
        "impersonator": "system:serviceaccount:mlops:release-debugger",
        "target_service_account": "champion-reader",
        "identity_permission": "impersonate:serviceaccount",
        "action_permissions": [
            "impersonate-on:serviceaccount:get",
            "impersonate-on:serviceaccount:list",
            "impersonate-on:serviceaccount:watch",
        ],
        "resources": ["deployments/status", "services", "pods/log"],
        "risk_control": "Support tooling can inspect champion health without inheriting release-manager patch or delete rights.",
    },
    {
        "name": "rollback-controller-patch-release-status",
        "namespace": "mlops",
        "impersonator": "system:serviceaccount:mlops:rollback-controller",
        "target_service_account": "release-status-writer",
        "identity_permission": "impersonate:serviceaccount",
        "action_permissions": [
            "impersonate-on:serviceaccount:get",
            "impersonate-on:serviceaccount:patch",
        ],
        "resources": ["deployments/status", "events"],
        "risk_control": "Rollback automation can patch release status but cannot create arbitrary workloads as the release identity.",
    },
]


def build_constrained_impersonation_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    feature = {
        "name": "ConstrainedImpersonation",
        "state": "Kubernetes v1.36 beta and enabled by default",
        "scope": "two-step authorization for impersonated identity plus scoped actions",
        "not_for": "broad legacy impersonate grants that inherit every target permission",
    }
    checks = [
        {
            "name": "beta_feature_status_recorded",
            "passed": feature["state"].startswith("Kubernetes v1.36 beta"),
            "evidence": "The plan records the feature status before relying on constrained impersonation.",
        },
        {
            "name": "identity_permission_is_separate",
            "passed": all(item["identity_permission"] == "impersonate:serviceaccount" for item in DELEGATIONS),
            "evidence": "Each delegation has an explicit service account identity grant.",
        },
        {
            "name": "action_permissions_are_constrained",
            "passed": all(
                all(verb.startswith("impersonate-on:serviceaccount:") for verb in item["action_permissions"])
                for item in DELEGATIONS
            ),
            "evidence": "Every delegated action uses impersonate-on service account verbs.",
        },
        {
            "name": "dangerous_verbs_excluded",
            "passed": all(
                not {"delete", "create"}.intersection({verb.rsplit(":", 1)[-1] for verb in item["action_permissions"]})
                for item in DELEGATIONS
            ),
            "evidence": "Debug and rollback delegation excludes broad create/delete authority.",
        },
        {
            "name": "audit_requirement_recorded",
            "passed": all(item["risk_control"] for item in DELEGATIONS),
            "evidence": "Each delegation documents the production risk it is narrowing.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_constrained_impersonation_for_release_debugging" if passed else "keep_legacy_impersonation_blocked",
        "passed": passed,
        "feature": feature,
        "delegations": DELEGATIONS,
        "checks": checks,
        "runbook": [
            "Grant impersonate:serviceaccount only for the exact target service account.",
            "Grant impersonate-on:serviceaccount verbs only for the resources and actions the workflow needs.",
            "Alert on legacy impersonate verbs that are not paired with constrained action grants.",
            "Inspect audit authenticationMetadata.impersonationConstraint during release or rollback investigations.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/",
        ],
    }
    write_json(root / "reports" / "constrained_impersonation_plan.json", plan)
    return plan
