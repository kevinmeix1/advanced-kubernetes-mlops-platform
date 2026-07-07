# Network Security

This project models a default-deny runtime boundary for the MLOps namespace. The local report explains the allowed communication graph, while the Kubernetes manifest shows the NetworkPolicy and Istio controls a production cluster would apply.

Run:

```bash
make network-security
```

The report is written to `.local/reports/network_security.json`.

## Controls

- Default deny for ingress and egress.
- Explicit DNS egress allow so service discovery keeps working.
- Allow-listed release-controller egress to MLflow and KServe.
- Predictor telemetry egress only to the OpenTelemetry collector.
- Istio namespace-level `PeerAuthentication` with `STRICT` mTLS.
- AuthorizationPolicy that limits release operations to the Airflow worker service account.

## References

Kubernetes NetworkPolicy allows all traffic until policies isolate pods; default-deny egress also blocks DNS unless allowed separately. Istio `PeerAuthentication` can require strict mutual TLS for namespace traffic. Gateway API security guidance recommends explicit authorization when traffic crosses ownership boundaries.
