# Reproducibility Results

작성일: 2026-05-25 KST

## 목적

clean clone 또는 CI 환경에서 네트워크 없이 최소 데이터 파이프라인을 재현할 수 있게 한다.

기존 MVP는 `data/` 이하 runtime artifact에 의존했다. 이 디렉터리는 git에 포함하지 않기 때문에, 새 환경에서는 바로 Airflow/backfill E2E를 실행할 수 없었다.

이번 작업은 production data pipeline이 아니라 **offline sample E2E 검증 경로**를 추가하는 것이다.

## 구현 파일

```text
pipelines/prepare_smoke_fixture.py
pipelines/run_smoke_e2e.py
pipelines/load_postgres.py
.github/workflows/ci.yml
```

## 구현 내용

### 1. Deterministic fixture generator

```text
pipelines/prepare_smoke_fixture.py
```

역할:

```text
네트워크 호출 없이 synthetic NHTSA-like raw JSON 생성
data/raw/smoke_test/<run_id>/ 아래에 complaints/recalls JSON 저장
summary.json과 reports/smoke_fixture_latest.md 생성
```

fixture 대상:

| make | model | year | component | complaints | recalls |
|---|---|---:|---|---:|---:|
| HYUNDAI | SANTA FE | 2022 | ENGINE | 15 | 2 |
| KIA | TELLURIDE | 2022 | ELECTRICAL SYSTEM | 15 | 2 |

### 2. Offline sample E2E runner

```text
pipelines/run_smoke_e2e.py
```

실행 순서:

```text
prepare_smoke_fixture
-> normalize_sample
-> build_features_sample
-> build_training_dataset_sample
-> train_baseline_sample
```

실행 명령:

```bash
python pipelines/run_smoke_e2e.py --run-id ci_fixture --top-k 5 --max-iter 1000
```

## 로컬 실행 결과

실행일:

```text
2026-05-25 KST
```

결과:

```text
Smoke E2E complete.
```

주요 산출:

```text
Normalized complaints rows: 30
Normalized recalls rows: 4
Feature rows: 77
Entity count: 2
Rows label-ready: 73
Positive rows: 26
Train rows: 46
Train positives: 23
Test rows: 27
Test positives: 3
Rule AP: 0.261905
Logistic AP: 1.0
```

주의:

```text
이 수치는 모델 성능 주장이 아니다.
fixture가 작고 synthetic이므로 CI smoke E2E 성공 여부만 확인한다.
```

Docker build도 로컬에서 확인했다.

```bash
docker compose build api
```

결과:

```text
Image vehicle-recall-risk-api:local Built
```

sample 산출물을 PostgreSQL에 적재하고 FastAPI 조회도 확인했다.

실행:

```bash
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
```

적재 결과:

```text
complaints: 30
recalls: 4
weekly_features: 77
training_dataset: 77
training_dataset_labeled_only: 73
latest_risk_scores: 2
baseline_test_predictions: 73
baseline_logistic_coefficients: 12
```

API smoke:

```text
GET /health/db: 200
GET /risk-scores/latest?limit=3: 200
```

sample API 응답 예:

```text
HYUNDAI SANTA FE 2022 ENGINE score=2.4749
KIA TELLURIDE 2022 ELECTRICAL SYSTEM score=2.4749
```

로컬 검증 후 개발 DB는 다시 full backfill 데이터로 복구했다.

## CI 변경

GitHub Actions에 다음 단계를 추가했다.

```text
python pipelines/run_smoke_e2e.py --run-id ci_fixture --top-k 5 --max-iter 1000
docker compose build api
docker compose up -d postgres
docker compose exec -T postgres pg_isready -U recall_user -d recall_risk
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
docker compose up -d api
curl http://localhost:28000/health/db
curl "http://localhost:28000/risk-scores/latest?limit=3"
```

CI가 확인하는 것:

```text
1. Python unit tests
2. offline sample E2E
3. FastAPI Docker image build
4. sample PostgreSQL load
5. API container DB/API smoke test
```

Node 20 deprecation warning 대응:

```text
actions/checkout@v6
actions/setup-python@v6
```

원격 GitHub Actions 실행도 확인했다.

```text
workflow: CI
status: completed
conclusion: success
head_sha: d05c20e30306f9f195e1a08d4f86b4a385a3f875
url: https://github.com/belucent0/vehicle-recall-risk-mlops/actions/runs/26410829848
```

## 현재 의미

이제 새 환경에서 최소한 다음 주장은 가능하다.

```text
clean clone에서도 네트워크 없이 sample raw JSON 생성부터 feature/label/model artifact 생성, PostgreSQL 적재, API 조회까지 실행할 수 있다.
```

다만 전체 backfill/Airflow/PostgreSQL E2E는 여전히 기존 runtime data 또는 별도 수집 단계가 필요하다.

## 남은 한계

```text
1. sample E2E는 Airflow를 사용하지 않는다.
2. sample E2E는 MLflow logging을 포함하지 않는다.
3. full backfill data는 git에 포함하지 않는다.
4. full backfill/Airflow/PostgreSQL E2E의 clean clone 재현은 아직 별도 작업이 필요하다.
```

## 다음 개선 후보

```text
1. sample E2E용 Airflow DAG 또는 DAG conf 추가
2. sample E2E에 MLflow logging 추가
3. collect_backfill/incremental collector를 Airflow DAG로 분리
4. GitHub Actions의 Node.js 20 deprecation warning 대응
```
