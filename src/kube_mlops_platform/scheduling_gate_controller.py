from __future__ import annotations

from pathlib import Path

from .io import write_json


GATED_PODS = [
    {
        "pod": "release-validation-controller",
        "namespace": "mlops",
        "owner": "airflow-release-dag",
        "age_minutes": 4,
        "gates": ["mlops.kevinmei.dev/release-evidence-ready"],
        "evidence": {
            "release_admission_decision": "ready",
            "dag_bundle_version": "ready",
            "asset_event": "ready",
        },
    },
    {
        "pod": "churn-canary-analysis",
        "namespace": "mlops",
        "owner": "kserve-canary-analysis",
        "age_minutes": 9,
        "gates": ["mlops.kevinmei.dev/model-cache-ready", "mlops.kevinmei.dev/gateway-route-accepted"],
        "evidence": {
            "model_cache_status": "ModelDownloaded",
            "gateway_route_condition": "Accepted",
            "endpoint_picker_health": "ready",
        },
    },
    {
        "pod": "batch-scoring-replay",
        "namespace": "mlops-batch",
        "owner": "airflow-replay-backfill",
        "age_minutes": 38,
        "gates": ["mlops.kevinmei.dev/kueue-admitted", "mlops.kevinmei.dev/replay-window-approved"],
        "evidence": {
            "kueue_admission": "Pending",
            "replay_window": "approved",
            "dra_allocation": "waiting_for_claim",
        },
    },
]


GATE_POLICY = {
    "max_gate_age_minutes": 30,
    "patch_strategy": "server_side_apply_status_patch",
    "patch_order": [
        "release evidence",
        "model cache and gateway route",
        "Kueue admission and DRA allocation",
    ],
    "observability": [
        "scheduler_pending_pods{queue=\"gated\"}",
        "mlops_scheduling_gate_age_seconds",
        "mlops_scheduling_gate_patch_total",
        "mlops_scheduling_gate_stale_total",
    ],
}


def _ready_for_release_validation(evidence: dict) -> bool:
    return all(value == "ready" for value in evidence.values())


def _ready_for_canary(evidence: dict) -> bool:
    return (
        evidence.get("model_cache_status") == "ModelDownloaded"
        and evidence.get("gateway_route_condition") == "Accepted"
        and evidence.get("endpoint_picker_health") == "ready"
    )


def _ready_for_replay(evidence: dict) -> bool:
    return (
        evidence.get("kueue_admission") == "Admitted"
        and evidence.get("replay_window") == "approved"
        and evidence.get("dra_allocation") == "allocated"
    )


def _ready(pod: dict) -> bool:
    if pod["pod"] == "release-validation-controller":
        return _ready_for_release_validation(pod["evidence"])
    if pod["pod"] == "churn-canary-analysis":
        return _ready_for_canary(pod["evidence"])
    return _ready_for_replay(pod["evidence"])


def build_scheduling_gate_controller_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    decisions = []
    for pod in GATED_PODS:
        ready = _ready(pod)
        stale = pod["age_minutes"] > GATE_POLICY["max_gate_age_minutes"]
        decisions.append(
            {
                **pod,
                "ready_to_schedule": ready,
                "stale": stale,
                "remaining_gates": [] if ready else pod["gates"],
                "action": "remove_scheduling_gates" if ready else ("create_stale_gate_incident" if stale else "keep_gated"),
            }
        )
    checks = [
        {
            "name": "controller_is_fail_closed",
            "passed": all(item["action"] != "remove_scheduling_gates" or item["ready_to_schedule"] for item in decisions),
            "evidence": "No gate is removed unless every prerequisite signal for that pod is ready.",
        },
        {
            "name": "stale_gate_incident_created",
            "passed": any(item["action"] == "create_stale_gate_incident" for item in decisions),
            "evidence": "Long-lived gates turn into incidents instead of invisible pending pods.",
        },
        {
            "name": "dra_allocation_blocks_replay",
            "passed": any(item["pod"] == "batch-scoring-replay" and "dra_allocation" in item["evidence"] and not item["ready_to_schedule"] for item in decisions),
            "evidence": "Replay pods stay unscheduled until their ResourceClaim is allocated.",
        },
        {
            "name": "observability_metrics_declared",
            "passed": len(GATE_POLICY["observability"]) >= 4,
            "evidence": ", ".join(GATE_POLICY["observability"]),
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": "run_scheduling_gate_controller" if passed else "keep_manual_gate_patch_runbook",
        "controller": {
            "name": "mlops-scheduling-gate-controller",
            "reconcile_interval_seconds": 15,
            "leader_election": True,
            "idempotency_key": "metadata.uid + schedulingGate.name + evidence.digest",
            "failure_mode": "fail_closed_keep_pod_scheduling_gated",
        },
        "policy": GATE_POLICY,
        "decisions": decisions,
        "summary": {
            "pods_observed": len(decisions),
            "gates_removed": sum(len(item["gates"]) for item in decisions if item["action"] == "remove_scheduling_gates"),
            "pods_released": sum(1 for item in decisions if item["action"] == "remove_scheduling_gates"),
            "pods_still_gated": sum(1 for item in decisions if item["action"] != "remove_scheduling_gates"),
            "stale_incidents": sum(1 for item in decisions if item["action"] == "create_stale_gate_incident"),
        },
        "checks": checks,
        "kubernetes_assets": [
            "kubernetes/scheduling-gate-controller.yaml",
            "kubernetes/pod-resource-envelopes.yaml",
        ],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
        ],
    }
    write_json(root / "reports" / "scheduling_gate_controller_plan.json", plan)
    return plan
