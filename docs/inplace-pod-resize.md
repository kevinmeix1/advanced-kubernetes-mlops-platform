# In-Place Pod Resize Controls

`make inplace-resize-plan` writes `.local/reports/inplace_resize_plan.json` and pairs it with `kubernetes/inplace-pod-resize.yaml`.

## What It Shows

- Kubernetes v1.35 stable in-place CPU and memory resizing through the `pods/resize` subresource.
- Kubernetes v1.36 beta in-place vertical scaling for pod-level resources through `spec.resources`.
- Container `resizePolicy` choices for non-disruptive CPU updates and restart-required memory updates.
- VPA `InPlaceOrRecreate` wiring for autoscaler-compatible resize recommendations.
- Alerts for `PodResizePending` and `PodResizeInProgress` so release automation can hold while cgroups converge.

## Production Notes

In-place resize is useful for canary startup boosts, temporary Ray analysis bursts, and warm rollback validation pods. It does not remove the need for capacity checks: if the node cannot admit the new request, Kubernetes marks `PodResizePending`; if the change is admitted but not fully applied, `PodResizeInProgress` remains true. The release controller should pause fanout while either condition is present.

The demo also separates CPU and memory behavior. CPU can often resize without a restart, while memory changes should respect `resizePolicy` and runtime constraints.

## References

- Kubernetes v1.35 in-place Pod Resize GA: <https://kubernetes.io/blog/2025/12/19/kubernetes-v1-35-in-place-pod-resize-ga/>
- Kubernetes v1.36 pod-level resource resize beta: <https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/>
- Kubernetes resize container resources task: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/>
