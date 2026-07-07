from __future__ import annotations

"""
Metaflow implementation sketch for the local training workflow.

Run in a full environment with:
    python metaflow_flows/train_churn_flow.py run
"""

try:
    from metaflow import FlowSpec, step
except Exception:  # Keeps the repo testable without installing Metaflow.
    class FlowSpec:  # type: ignore
        pass

    def step(func):  # type: ignore
        return func


class ChurnTrainingFlow(FlowSpec):
    @step
    def start(self):
        from pathlib import Path
        from kube_mlops_platform.cli import train

        self.output_dir = Path(".local")
        self.train_result = train(self.output_dir)
        self.next(self.evaluate)

    @step
    def evaluate(self):
        from kube_mlops_platform.cli import evaluate

        self.evaluation = evaluate(self.output_dir)
        self.next(self.deploy)

    @step
    def deploy(self):
        from kube_mlops_platform.cli import deploy

        if self.evaluation["gate_report"]["passed"]:
            self.deployment = deploy(self.output_dir)
        else:
            self.deployment = {"status": "skipped", "reason": "gates_failed"}
        self.next(self.end)

    @step
    def end(self):
        print({"evaluation": self.evaluation, "deployment": self.deployment})


if __name__ == "__main__":
    ChurnTrainingFlow()
