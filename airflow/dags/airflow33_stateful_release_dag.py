"""Airflow 3.3 stateful release orchestration.

CI parses this module against Apache Airflow 3.3. The local dependency-light
demo does not start Airflow services, but this is executable DAG-authoring code
rather than a pseudocode sketch.
"""

from __future__ import annotations

from datetime import timedelta

from airflow.sdk import (
    NEVER_EXPIRE,
    Asset,
    DAG,
    ExceptionRetryPolicy,
    FanOutMapper,
    FixedKeyMapper,
    MinimumCount,
    PartitionedAssetTimetable,
    PartitionedAtRuntime,
    RetryAction,
    RetryRule,
    RollupMapper,
    SegmentWindow,
    StartOfWeekMapper,
    WeekWindow,
    asset,
    task,
)


AIRFLOW_33_DAG_IDS = {
    "stateful_release_evidence_rollup",
    "candidate_daily_canary_fanout",
}
RELEASE_SEGMENTS = ["feature-evaluation", "canary-observation", "governance-evidence"]

RELEASE_RETRY_POLICY = ExceptionRetryPolicy(
    rules=[
        RetryRule(
            exception=ConnectionError,
            action=RetryAction.RETRY,
            retry_delay=timedelta(seconds=30),
            reason="Transient control-plane connection failure",
        ),
        RetryRule(
            exception=PermissionError,
            action=RetryAction.FAIL,
            reason="Authorization failures require operator intervention",
        ),
    ],
)

RELEASE_EVIDENCE_SEGMENTS = Asset.ref(name="release_evidence_segments")
RELEASE_DECISION = Asset(
    uri="s3://mlops/release/churn-risk/stateful-decision.json",
    name="stateful_release_decision",
)
WEEKLY_CANDIDATE = Asset(
    uri="mlflow://models/churn-risk/weekly-candidate",
    name="weekly_churn_candidate",
)


@asset(
    uri="s3://mlops/release/churn-risk/evidence-segments.json",
    schedule=PartitionedAtRuntime(),
)
def release_evidence_segments(self, outlet_events) -> None:
    """Emit the evidence partitions discovered by the release preflight."""

    outlet_events[self].add_partitions(RELEASE_SEGMENTS)


with DAG(
    dag_id="stateful_release_evidence_rollup",
    schedule=PartitionedAssetTimetable(
        assets=RELEASE_EVIDENCE_SEGMENTS,
        default_partition_mapper=RollupMapper(
            upstream_mapper=FixedKeyMapper("release-ready"),
            window=SegmentWindow(RELEASE_SEGMENTS),
            wait_policy=MinimumCount(len(RELEASE_SEGMENTS)),
            max_downstream_keys=1,
        ),
    ),
    catchup=False,
    max_active_runs=1,
    params={"candidate_digest": "sha256:replace-at-trigger-time"},
    tags=["airflow-3.3", "state-store", "asset-rollup", "release"],
) as stateful_release_evidence_rollup:

    @task(
        inlets=[RELEASE_EVIDENCE_SEGMENTS],
        outlets=[RELEASE_DECISION],
        retries=4,
        retry_delay=timedelta(minutes=1),
        retry_policy=RELEASE_RETRY_POLICY,
    )
    def checkpoint_release_decision(**context) -> dict[str, str]:
        task_store = context["task_state_store"]
        operation_id = task_store.get("release_operation_id")
        if operation_id is None:
            operation_id = f"release:{context['run_id']}"
            task_store.set("release_operation_id", operation_id, retention=NEVER_EXPIRE)

        task_store.set(
            "release_progress",
            {"stage": "evidence_complete", "attempt": context["ti"].try_number},
        )
        decision_store = context["asset_state_store"][RELEASE_DECISION]
        decision_store.set("candidate_digest", context["params"]["candidate_digest"])
        decision_store.set("last_release_operation_id", operation_id)
        return {"operation_id": operation_id, "status": "ready_for_release_policy"}

    checkpoint_release_decision()


with DAG(
    dag_id="candidate_daily_canary_fanout",
    schedule=PartitionedAssetTimetable(
        assets=WEEKLY_CANDIDATE,
        default_partition_mapper=FanOutMapper(
            upstream_mapper=StartOfWeekMapper(),
            window=WeekWindow(),
            max_downstream_keys=7,
        ),
    ),
    catchup=False,
    max_active_runs=2,
    tags=["airflow-3.3", "asset-fanout", "canary"],
) as candidate_daily_canary_fanout:

    @task(inlets=[WEEKLY_CANDIDATE], retries=2, retry_policy=RELEASE_RETRY_POLICY)
    def validate_daily_canary_partition(dag_run=None) -> dict[str, str | None]:
        return {
            "partition_key": dag_run.partition_key if dag_run else None,
            "candidate_asset": WEEKLY_CANDIDATE.uri,
            "validation": "bounded_daily_canary",
        }

    validate_daily_canary_partition()
