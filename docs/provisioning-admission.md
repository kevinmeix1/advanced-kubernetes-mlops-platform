# Kueue Provisioning Admission

This project already models Kueue quota and Airflow release gates. Provisioning admission adds the missing production check: a release should not advance merely because quota is available; it should advance only when the cluster can actually provision the capacity needed for training, scoring, canary analysis, and rollback smoke.

## Release Admission Flow

1. Airflow submits a candidate release wave with a Kueue queue label.
2. Kueue reserves ClusterQueue quota for CPU or GPU release flavors.
3. The built-in provisioning admission controller creates a `ProvisioningRequest`.
4. Cluster Autoscaler checks real node availability and provisioning options.
5. The release wave runs only when the AdmissionCheck is `Ready`.
6. Failed or expired provisioning freezes promotion and preserves the champion model alias.

## Controls

- `AdmissionCheck` uses the built-in `kueue.x-k8s.io/provisioning-request` controller.
- `ProvisioningRequestConfig` declares `provisioningClassName`, `managedResources`, retry backoff, `podSetMergePolicy`, and `podSetUpdates`.
- `admissionChecksStrategy` scopes capacity checks to expensive release flavors.
- Jobs set `provreq.kueue.x-k8s.io/maxRunDurationSeconds` so bookings cannot drift indefinitely.
- Prometheus alerts cover pending checks, retry exhaustion, and booking expiry.

## Operational Semantics

| Signal | Release action |
| --- | --- |
| `Provisioned=true` | Continue candidate training, scoring, and canary evidence. |
| `Provisioned=false` | Keep the wave suspended and alert capacity owner. |
| `Failed=true` | Release quota, freeze promotion, and retry smaller recovery work. |
| `BookingExpired=true` | Re-run rollback smoke before allowing a wider release wave. |
| `CapacityRevoked=true` | Treat as an incident and keep champion traffic active. |

## Why This Matters

Logical queue quota is about fairness. Provisioning admission is about runnable capacity. Senior MLOps systems need both, especially when a release depends on GPU canary analysis or bounded rollback validation.
