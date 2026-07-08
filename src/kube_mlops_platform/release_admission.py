from __future__ import annotations

from pathlib import Path

from .io import read_json, write_json


def _load(path: Path, default: dict) -> dict:
    return read_json(path) if path.exists() else default


def _check(name: str, passed: bool, observed: object, *, owner: str, action: str) -> dict:
    return {
        "name": name,
        "passed": passed,
        "observed": observed,
        "owner": owner,
        "action": action if not passed else "none",
    }


def evaluate_release_admission(
    *,
    slo: dict,
    performance: dict,
    queue: dict,
    governance: dict,
    supply_chain: dict,
    release_plan: dict,
) -> dict:
    max_burn = float(slo.get("max_burn_rate", 0.0))
    release_freeze = bool(slo.get("release_freeze", False))
    performance_passed = bool(performance.get("passed", False))
    queue_passed = bool(queue.get("passed", False))
    critical_pending = [
        item["name"]
        for item in queue.get("simulation", {}).get("pending", [])
        if int(item.get("priority", 0)) >= 900
    ]
    governance_decision = governance.get("release", {}).get("decision", "unknown")
    attestation_ready = (
        int(supply_chain.get("artifact_count", 0)) > 0
        and supply_chain.get("subject", {}).get("attestation_action") == "actions/attest@v4"
    )
    release_action = release_plan.get("recommended_action", "unknown")
    checks = [
        _check(
            "slo_error_budget",
            not release_freeze and max_burn < 6.0,
            {"max_burn_rate": max_burn, "recommended_action": slo.get("recommended_action")},
            owner="serving",
            action="freeze_promotion",
        ),
        _check(
            "performance_budget",
            performance_passed,
            {"failed": [check["name"] for check in performance.get("checks", []) if not check.get("passed")]},
            owner="ml-platform",
            action="hold_canary",
        ),
        _check(
            "queue_admission",
            queue_passed and not critical_pending,
            {"pending_count": queue.get("pending_count", 0), "critical_pending": critical_pending},
            owner="orchestration",
            action="reserve_rollback_capacity",
        ),
        _check(
            "governance_approval",
            governance_decision == "approved_for_champion",
            governance_decision,
            owner="risk",
            action="require_approval_record",
        ),
        _check(
            "supply_chain_attestation",
            attestation_ready,
            supply_chain.get("subject", {}),
            owner="platform-security",
            action="wait_for_provenance",
        ),
    ]
    if release_freeze or max_burn >= 14.4:
        action = "freeze_promotion"
    elif release_action == "rollback":
        action = "rollback_champion"
    elif not queue_passed or critical_pending:
        action = "throttle_release_queue"
    elif all(check["passed"] for check in checks):
        action = "admit_canary"
    else:
        action = "hold_canary"
    return {
        "recommended_action": action,
        "admitted": action == "admit_canary",
        "unsafe_allow": action == "admit_canary" and not all(check["passed"] for check in checks),
        "checks": checks,
        "release_plan_action": release_action,
        "failure_policy": "fail_closed",
    }


def build_release_admission_decision(root: str | Path) -> dict:
    root = Path(root)
    decision = evaluate_release_admission(
        slo=_load(root / "reports" / "slo_error_budget.json", {}),
        performance=_load(root / "reports" / "performance_budget.json", {}),
        queue=_load(root / "reports" / "queue_simulation.json", {}),
        governance=_load(root / "reports" / "governance_evidence_bundle.json", {}),
        supply_chain=_load(root / "reports" / "supply_chain_evidence.json", {}),
        release_plan=_load(root / "reports" / "release_control_plan.json", {}),
    )
    record = {
        "project": "Kubernetes MLOps Platform",
        "target": "kserve://mlops/churn-risk-predictor",
        "evaluated_at": "2026-07-08T00:00:00Z",
        "decision": decision,
        "policy_inputs": {
            "slo": "reports/slo_error_budget.json",
            "performance": "reports/performance_budget.json",
            "queue": "reports/queue_simulation.json",
            "governance": "reports/governance_evidence_bundle.json",
            "supply_chain": "reports/supply_chain_evidence.json",
            "release_plan": "reports/release_control_plan.json",
        },
        "enforcement_points": [
            "Airflow release DAG short-circuits promotion unless the decision is admit_canary.",
            "Kubernetes ValidatingAdmissionPolicy requires release-decision and evidence-sha annotations.",
            "Argo Rollouts analysis reads Prometheus burn-rate and latency signals before traffic advances.",
            "Kueue and Airflow pools reserve rollback capacity before admitting non-critical work.",
        ],
        "references": [
            "https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/",
            "https://argo-rollouts.readthedocs.io/en/stable/features/analysis/",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
        ],
    }
    write_json(root / "reports" / "release_admission_decision.json", record)
    return record
