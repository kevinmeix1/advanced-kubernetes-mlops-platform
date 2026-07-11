# Operations Review Runbook

## Start the full evidence dashboard

```bash
make clean
make demo

python3.12 -m venv .venv-mlflow
.venv-mlflow/bin/pip install --constraint requirements-mlflow.lock -e '.[mlflow3]'
make mlflow-contract PYTHON=.venv-mlflow/bin/python

python3 -m http.server 8091 --bind 127.0.0.1 --directory .local/reports
```

Open `http://127.0.0.1:8091/mlops_platform_dashboard.html`.

The dashboard includes a **Run Review** panel. Each cue maps the narrated recording to the release lab,
observability signals, and generated JSON evidence.

## Five-minute story

1. Establish the executable evidence boundary: lifecycle, MLflow registry, and Airflow SDK contract versus cluster architecture labs.
2. Point to champion application version, KServe state, MLflow 3.14 contract, p95 latency, and observed drift.
3. Explain why observed drift produces HOLD despite passing offline gates.
4. Turn Feature drift checks on and show all five controls plus the Airflow-to-KServe path move to ADVANCE CANARY.
5. Raise Error rate to 6% and connect the 12x burn to ROLLBACK and the previous-champion alias.
6. Finish with registry idempotency, conflict detection, loaded-model parity, and the production Kubernetes boundary.

## Generate narration and video

```bash
python3.11 -m venv .demo-venv
.demo-venv/bin/pip install -e '.[demo]'
make demo-voice PYTHON=.demo-venv/bin/python
make demo-video
```

The neural voice is generated with `edge-tts` in a media-only environment. The
voice uses a natural neural speaker, emits subtitle timing, and keeps the media
dependencies away from the runtime environment. Local offline options such as
Piper or Kokoro can replace the voice step, but `edge-tts` keeps the committed
demo small and reproducible. The resulting video is
`docs/demo/kubernetes-mlops-judge-demo.mp4`.
