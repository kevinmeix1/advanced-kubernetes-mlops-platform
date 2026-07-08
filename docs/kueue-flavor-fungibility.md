# Kueue Flavor Fungibility

`make flavor-fungibility` writes `.local/reports/flavor_fungibility_plan.json` and pairs it with `kubernetes/kueue-flavor-fungibility.yaml`.

## What It Shows

- `ResourceFlavor` objects for spot CPU, on-demand CPU, reserved L4 GPU, and spot L4 GPU capacity.
- `ClusterQueue.spec.flavorFungibility.whenCanBorrow: TryNextFlavor`.
- `ClusterQueue.spec.flavorFungibility.whenCanPreempt: TryNextFlavor`.
- Explicit `flavorFungibility.preference: BorrowingOverPreemption`.
- Different flavor order for release validation, batch scoring, and GPU canary analysis.

## Production Notes

Static ClusterQueues make reviewers wonder what happens when a cheap or preferred pool is saturated. Flavor fungibility answers that question directly: Kueue can try the next flavor before borrowing from the cohort or preempting an already admitted workload.

The model lifecycle platform uses different orders by workload type. Release validation prefers stable on-demand nodes before spot. Batch scoring uses spot first and only falls back to on-demand when the cheap pool is saturated. GPU canary analysis prefers reserved L4 slices and tries spot GPU before it disrupts lower-priority diagnostics.

## References

- Kueue ClusterQueue: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue ResourceFlavor: <https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/>
- Kueue FlavorFungibility API: <https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#flavorfungibility>
