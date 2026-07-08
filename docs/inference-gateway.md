# Gateway API Inference Extension

`make inference-gateway-plan` writes `.local/reports/inference_gateway_plan.json` and pairs it with `kubernetes/inference-gateway-routing.yaml`.

## What It Shows

- Stable v1 `InferencePool` routing for churn model-server pods.
- Endpoint Picker integration with `FailOpen` fallback to the existing KServe route.
- Alpha `InferenceObjective` examples for online churn scoring and bulk replay.
- Gateway API `HTTPRoute` backend references that target an `InferencePool`.
- Alerts for endpoint-picker unavailability during release gates.

## Production Notes

The release platform already has KServe canary controls. Gateway API Inference Extension adds model-aware endpoint selection when replicas expose useful signals such as queue depth, readiness, cache status, or route priority. The project treats `InferencePool` as the stable API and documents `InferenceObjective` as an alpha priority experiment.

References: Kubernetes Gateway API Inference Extension, InferencePool v1 docs, and Istio integration guide.
