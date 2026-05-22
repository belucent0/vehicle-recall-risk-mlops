# MVP Summary

작성일: 2026-05-15 KST

## 프로젝트 한 줄 요약

```text
미국 NHTSA consumer complaints와 recall records를 이용해 차량/부품 단위 리콜 조기경보 dataset과 baseline score를 만든다.
```

## MVP의 정체

이 MVP는 완성형 MLOps 서비스가 아니다.

정확히는:

```text
데이터 수집 가능성
정규화 가능성
feature/label 생성 가능성
baseline 평가 가능성
최신 risk score report 생성 가능성
```

을 검증한 end-to-end MVP다.

## 완료한 흐름

```text
1. NHTSA API smoke test
2. raw JSON 정규화
3. weekly feature 생성
4. 90일 recall label 생성
5. smoke baseline 평가
6. VPIC vehicle model list 수집
7. model alias 확인
8. MVP vehicle model 후보 정제
9. MVP backfill 수집
10. MVP backfill 정규화
11. MVP feature/label 생성
12. MVP baseline 재평가
13. 최신 risk score report 생성
```

## 핵심 산출물

```text
data/interim/backfill/20260515T114046Z/complaints.csv
data/interim/backfill/20260515T114046Z/recalls.csv
data/processed/backfill/20260515T114046Z/weekly_features.csv
data/processed/backfill/20260515T114046Z/training_dataset.csv
data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv
reports/latest_risk_score_report.md
```

## 주요 수치

| 항목 | 값 |
|---|---:|
| MVP unique vehicle-year | 917 |
| complaints rows | 103,440 |
| recalls rows | 3,018 |
| weekly feature rows | 1,189,569 |
| entity count | 8,091 |
| label-ready rows | 1,172,332 |
| positive rows | 4,348 |
| positive rate | 0.003709 |
| test rows | 293,083 |
| test positives | 1,611 |
| rule baseline AP | 0.006281 |
| logistic baseline AP | 0.008251 |

## 평가 결과 해석

positive rate가 약 0.37%이므로 이 문제는 rare event prediction이다.

따라서 다음 지표가 중요하다.

```text
Average Precision
Precision@K
Recall@K
Calibration
Lead time
```

이번 MVP에서 logistic baseline은 Average Precision 기준으로 rule baseline보다 약간 높았다.

```text
rule AP: 0.006281
logistic AP: 0.008251
```

하지만 logistic top-k 결과는 좋지 않았다. score가 1.0으로 포화되는 false positive가 있었기 때문에 calibration과 feature 개선이 필요하다.

## 최신 risk score

최신 기준 week:

```text
2026-05-11
```

최신 report:

```text
reports/latest_risk_score_report.md
docs/LATEST_RISK_SCORE_RESULTS.md
```

주의:

```text
baseline_risk_score는 리콜 확률이 아니라 complaint spike signal이다.
```

## 알게 된 것

1. NHTSA API 기반으로 이 프로젝트는 실제 구현 가능하다.
2. complaints와 recalls를 차량/부품/week 단위로 연결할 수 있다.
3. 리콜은 매우 희귀한 이벤트라 accuracy는 의미 없다.
4. VPIC model list에는 노이즈가 있어 후보 정제가 필요하다.
5. 일부 모델은 endpoint coverage 문제가 있다. 특히 F-150은 recalls는 많지만 complaints 조회가 비어 있다.
6. 현재 MVP baseline은 아직 예측 모델이라기보다 조기경보 dataset과 baseline scoring framework다.

## MVP 이후 할 일

MLOps 포트폴리오화:

```text
PostgreSQL 저장
Airflow scheduling
MLflow experiment tracking
FastAPI serving
Dashboard
CI/Docker
```

2026-05-16 결정:

```text
PostgreSQL을 메인 저장소로 사용한다.
DuckDB는 도입하지 않는다.
```

모델/데이터 개선:

```text
component mapping 개선
NHTSA investigations 추가
manufacturer communications 추가
lead-time metric 추가
calibration 개선
F-150 endpoint coverage 우회 방법 조사
```
