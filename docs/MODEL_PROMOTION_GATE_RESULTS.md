# Model Promotion Gate Results

- Source run ID: `20260515T114046Z`
- Evaluated at UTC: `2026-06-01T13:52:07.447356+00:00`
- Promotion status: `approved`

## Gate config

| Setting | Value |
|---|---:|
| min_test_positives | 10 |
| min_ap_delta | 0.0 |
| max_brier_regression | 0.0 |
| precision_k | 25 |
| require_precision_at_k | False |

## Metrics

| Metric | Value |
|---|---:|
| rule_average_precision | 0.006281 |
| logistic_average_precision | 0.008191 |
| average_precision_delta | 0.00191 |
| rule_brier_score | 0.240245 |
| logistic_brier_score | 0.236554 |
| brier_score_delta | -0.003691 |
| rule_precision_at_25 | 0.08 |
| logistic_precision_at_25 | 0.0 |
| rule_hits_at_25 | 2.0 |
| logistic_hits_at_25 | 0.0 |
| test_row_count | 293083 |
| test_positive_count | 1611 |

## Blocking checks

| Check | Passed | Actual | Expected |
|---|---:|---:|---:|
| model_artifact_exists | True | data/processed/backfill/20260515T114046Z/sklearn_logistic_pipeline.joblib | existing model artifact |
| predictions_csv_exists | True | data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv | existing prediction CSV |
| test_positive_count | True | 1611 | >= 10 |
| logistic_ap_not_worse_than_rule | True | 0.00191 | >= 0.0 |
| logistic_brier_not_worse_than_rule | True | -0.003691 | <= 0.0 |

## Warnings

| Warning | Passed | Actual | Expected | Rule hits | Logistic hits |
|---|---:|---:|---:|---:|---:|
| logistic_precision_at_25_not_worse_than_rule | False | 0.0 | >= 0.08 | 2.0 | 0.0 |

## Interpretation

- Approved means the model is allowed to produce latest-week serving scores.
- Rejected means the DAG should stop before `score_latest` publishes model scores.
- Current default gate blocks on AP/Brier/test-size checks and warns on top-K precision.
- Tighten `--require-precision-at-k` after the ranking model improves.