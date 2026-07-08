# Workload Identity and Secretless Access

This platform models production access without static cloud keys in pods. Airflow release tasks, KServe predictors, and Metaflow workers each get their own Kubernetes `ServiceAccount`, namespace-scoped RBAC, projected one-hour tokens, and a federated cloud role.

## Controls

- `kubernetes/workload-identity.yaml` disables default service account token automounting and documents projected token expectations.
- `SecretStore` and `ExternalSecret` examples show provider-backed secret synchronization with a 30 minute refresh window.
- Airflow task identity is explicit through `service_account_name` policy rather than inherited scheduler permissions.
- SPIFFE IDs document service identity boundaries for future mTLS or SPIRE integration.
- `.local/reports/identity_access_report.json` proves that token TTL, ExternalSecret refresh, RBAC scope, SPIFFE IDs, and static-key avoidance pass.

## Production Notes

On AWS, map the service accounts to IRSA roles. On Azure, replace the role annotations with Azure Workload Identity labels and client IDs. On GKE, map the same identities through Workload Identity Federation. Keep static secrets limited to break-glass paths and alert if any runtime workload mounts a provider access key.

References: Kubernetes service account token projection, External Secrets Operator, SPIFFE/SPIRE, and Airflow KubernetesPodOperator service-account configuration.
