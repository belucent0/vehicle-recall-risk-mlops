# Model Version Metadata Results

Written: 2026-05-31 KST

## Purpose

This document records the first model/scoring metadata implementation for the
Vehicle Recall Risk MLOps project.

The goal was to make prediction and serving outputs answer these questions:

```text
Which data run produced this score?
Which scoring/model version produced this score?
When was it scored?
Which method produced it?
```

## Implemented files

```text
src/recall_risk/features/weekly_features.py
src/recall_risk/models/baseline.py
src/recall_risk/storage/postgres.py
src/recall_risk/serving/app.py
pipelines/build_features_sample.py
pipelines/build_features_labels_backfill.py
pipelines/train_baseline_sample.py
pipelines/train_baseline_backfill.py
pipelines/generate_latest_risk_report.py
infra/postgres/initdb/001_schema.sql
```

## Added metadata

### latest_risk_scores

```text
source_run_id
model_version
scoring_method
scored_at_utc
```

Current rule-score metadata:

```text
model_version: rule_baseline_v1
scoring_method: complaint_spike_rule
```

### baseline_test_predictions

```text
source_run_id
model_version
model_type
model_library
scored_at_utc
```

Current logistic baseline metadata:

```text
model_version: sklearn_logistic_v1
model_type: sklearn_logistic_regression_pipeline
model_library: scikit-learn
```

### baseline_logistic_coefficients

```text
source_run_id
model_version
model_type
model_library
scored_at_utc
```

## API response change

`GET /risk-scores/latest` now includes:

```text
load_run_id
source_run_id
model_version
scoring_method
scored_at_utc
```

Example:

```json
{
  "load_run_id": "20260515T114046Z",
  "source_run_id": "20260515T114046Z",
  "model_version": "rule_baseline_v1",
  "scoring_method": "complaint_spike_rule",
  "scored_at_utc": "2026-05-31T11:38:41.187996Z",
  "rank": 1,
  "make": "FORD",
  "model": "BRONCO SPORT",
  "model_year": 2021,
  "component": "UNKNOWN OR OTHER",
  "week_start": "2026-05-11",
  "baseline_risk_score": 2.8062
}
```

## Local verification

Smoke E2E:

```powershell
python pipelines/run_smoke_e2e.py --run-id ci_fixture --top-k 5 --max-iter 1000
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
```

Verified smoke metadata:

```text
load_run_id: ci_fixture
source_run_id: ci_fixture
model_version: rule_baseline_v1
scoring_method: complaint_spike_rule
v_latest_risk_scores rows: 2
```

Full MVP artifact regeneration and load:

```powershell
python pipelines/build_features_labels_backfill.py --run-id 20260515T114046Z --data-as-of-date 2026-05-15
python pipelines/train_baseline_backfill.py --run-id 20260515T114046Z --epochs 120 --negative-ratio 20 --max-train-rows 100000
python pipelines/generate_latest_risk_report.py --run-id 20260515T114046Z --top-k 25
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

Verified full metadata:

| Output | load_run_id | source_run_id | model_version | method/type | Rows |
|---|---|---|---|---|---:|
| v_latest_risk_scores | 20260515T114046Z | 20260515T114046Z | rule_baseline_v1 | complaint_spike_rule | 25 |
| baseline_test_predictions | 20260515T114046Z | 20260515T114046Z | sklearn_logistic_v1 | sklearn_logistic_regression_pipeline | 293,083 |
| baseline_logistic_coefficients | 20260515T114046Z | 20260515T114046Z | sklearn_logistic_v1 | sklearn_logistic_regression_pipeline | 12 |

API verification:

```text
GET /risk-scores/latest?limit=3: 200
```

## Why this matters

This creates a minimal model lineage layer:

```text
data run -> scoring/model version -> prediction row -> serving API response
```

This is required before splitting training and scoring DAGs, because scoring
outputs need stable metadata to identify which model/scoring rule produced them.

## Remaining gap

Training and scoring are still coupled in the current baseline script.

Next:

```text
1. Split training into a model artifact-producing step.
2. Add a dedicated batch scoring step.
3. Persist model_version/model_uri in MLflow and prediction metadata.
```
