# Model Latest Risk Score Results

- Source run ID: `20260515T114046Z`
- Scored at UTC: `2026-06-01T13:52:30.002831+00:00`
- Latest week: `2026-05-11`
- Model version: `sklearn_logistic_v1`
- Model type: `sklearn_logistic_regression_pipeline`
- Scoring method: `sklearn_logistic_latest_week`
- Promotion decision: `data/processed/backfill/20260515T114046Z/model_promotion_decision.json`
- Model artifact: `data/processed/backfill/20260515T114046Z/sklearn_logistic_pipeline.joblib`
- Input CSV: `data/processed/backfill/20260515T114046Z/weekly_features.csv`
- Output CSV: `data/processed/backfill/20260515T114046Z/model_latest_risk_scores.csv`

## What changed

The latest-week ranking below is produced by the trained scikit-learn logistic
pipeline, not by the rule-only complaint spike score.

## Top Model Risk Scores

| Rank | Make | Model | Year | Component | Week | Complaints | Rule score | Logistic score |
|---:|---|---|---:|---|---:|---:|---:|---:|
| 1 | HYUNDAI | IONIQ 5 | 2025 | ELECTRICAL SYSTEM | 2026-05-11 | 2 | 0.0 | 0.99744304 |
| 2 | FORD | ESCAPE | 2018 | ENGINE | 2026-05-11 | 4 | 0.0 | 0.99689495 |
| 3 | FORD | ESCAPE | 2016 | BACK OVER PREVENTION | 2026-05-11 | 2 | 0.0 | 0.99291146 |
| 4 | FORD | ESCAPE | 2017 | ENGINE | 2026-05-11 | 4 | 0.195 | 0.99156816 |
| 5 | TOYOTA | HIGHLANDER | 2021 | POWER TRAIN | 2026-05-11 | 1 | 0.0 | 0.98073349 |
| 6 | HYUNDAI | PALISADE | 2025 | AIR BAGS | 2026-05-11 | 1 | 0.0 | 0.98004507 |
| 7 | FORD | EDGE | 2017 | SERVICE BRAKES | 2026-05-11 | 1 | 0.0 | 0.96616765 |
| 8 | FORD | EDGE | 2019 | POWER TRAIN | 2026-05-11 | 1 | 0.0 | 0.96294039 |
| 9 | FORD | EXPLORER | 2020 | POWER TRAIN | 2026-05-11 | 2 | 0.0595 | 0.95500036 |
| 10 | FORD | EXPLORER | 2016 | STRUCTURE | 2026-05-11 | 2 | 0.1705 | 0.94690538 |
| 11 | FORD | ESCAPE | 2019 | ENGINE | 2026-05-11 | 1 | 0.0 | 0.94606127 |
| 12 | FORD | EDGE | 2015 | SERVICE BRAKES | 2026-05-11 | 1 | 0.0 | 0.93525925 |
| 13 | TOYOTA | HIGHLANDER | 2019 | POWER TRAIN | 2026-05-11 | 2 | 0.0 | 0.92678004 |
| 14 | FORD | EXPLORER | 2015 | STRUCTURE | 2026-05-11 | 1 | 0.0 | 0.92605439 |
| 15 | HYUNDAI | IONIQ 5 | 2022 | ELECTRICAL SYSTEM | 2026-05-11 | 1 | 0.0 | 0.91492725 |
| 16 | TOYOTA | HIGHLANDER | 2020 | POWER TRAIN | 2026-05-11 | 2 | 0.9991 | 0.88959824 |
| 17 | TOYOTA | C-HR | 2018 | POWER TRAIN | 2026-05-11 | 2 | 0.3536 | 0.88428129 |
| 18 | FORD | ESCAPE | 2017 | ENGINE AND ENGINE COOLING | 2026-05-11 | 2 | 1.0801 | 0.87205387 |
| 19 | FORD | EDGE | 2018 | ENGINE | 2026-05-11 | 2 | 1.3481 | 0.87007908 |
| 20 | FORD | EDGE | 2016 | SERVICE BRAKES | 2026-05-11 | 1 | 0.0 | 0.86418556 |
| 21 | HYUNDAI | PALISADE | 2022 | SEAT BELTS | 2026-05-11 | 2 | 1.3229 | 0.86259871 |
| 22 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2 | 2.8062 | 0.85964657 |
| 23 | TOYOTA | CAMRY | 2018 | POWER TRAIN | 2026-05-11 | 2 | 1.3481 | 0.85585543 |
| 24 | TOYOTA | HIGHLANDER | 2018 | POWER TRAIN | 2026-05-11 | 2 | 2.1841 | 0.85265757 |
| 25 | KIA | SEDONA | 2017 | ENGINE | 2026-05-11 | 1 | 0.9677 | 0.83889817 |

## Interpretation

- This is a production-like batch scoring path for the trained model.
- The logistic score is not yet calibrated as a real recall probability.
- The endpoint should be treated as a ranking signal until calibration and backtesting improve.
- The next step is to make scoring consume an MLflow model artifact or alias.