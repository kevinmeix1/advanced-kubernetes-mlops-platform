# Governance Evidence

This project now generates an auditable release evidence bundle with:

- `governance/model_card.json`
- `governance/data_card.json`
- `governance/risk_register.json`
- `governance/approval_record.json`
- `governance/reproducibility_manifest.json`
- `reports/governance_evidence_bundle.json`

The design follows three current production expectations:

- NIST AI RMF style risk work: Govern, Map, Measure, and Manage are represented in the bundle.
- MLflow registry practice: evidence refers to explicit model versions and alias-like champion metadata.
- Model card and datasheet practice: model behavior, intended use, limitations, and dataset provenance are machine-readable.

Run it locally:

```bash
make demo
make governance-bundle
```

The Kubernetes overlay in `kubernetes/governance-evidence.yaml` models how this becomes a release job and quarterly governance review in a real cluster.
