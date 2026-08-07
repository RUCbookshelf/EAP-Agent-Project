# 08 — Reproducibility

## One documented sequence

```powershell
# 1. create isolated environment (once)
python -m venv A:\EAP Agent Project\tmp\stage5-venv
A:\EAP Agent Project\tmp\stage5-venv\Scripts\python.exe -m pip install pytest spacy xlrd pyreadstat pandas
A:\EAP Agent Project\tmp\stage5-venv\Scripts\python.exe -m pip install `
  https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# 2. rebuild all Stage-5 artifacts
A:\EAP Agent Project\tmp\stage5-venv\Scripts\python.exe scripts\corpus_intelligence\build_stage5.py

# 3. verify
A:\EAP Agent Project\tmp\stage5-venv\Scripts\python.exe -m pytest tests\corpus --confcutdir=tests\corpus -q
```

No manual editing between steps. The build verifies the manifest hash before
any processing and records it in every artifact.

## Reproducibility chain

corpus package + manifest hash + FeatureSetVersion + ReferenceGroupVersion +
duplicate policy + distribution algorithm version -> snapshots,
memberships, distributions, version manifests. Re-running unchanged inputs
produces byte-identical data artifacts (feature snapshots, membership CSV, distribution JSONL) - deterministic order: sorted document/feature and group/feature records. Version manifests that carry a build timestamp (distribution_version.json) intentionally differ between runs.

## Evidence

Build rerun check (WU8): run build_stage5.py twice and compare
reference_distributions.jsonl hashes - see 09 for the recorded result.
