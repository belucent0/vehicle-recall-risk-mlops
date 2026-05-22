# FastAPI Read API Results

작성일: 2026-05-20 KST

## 목적

PostgreSQL에 적재한 MVP 산출물을 FastAPI에서 읽어 JSON API로 반환한다.

이번 단계는 모델 serving이 아니다. 이미 계산된 `latest_risk_scores`를 PostgreSQL에서 조회하는 **읽기 전용 API**를 만드는 단계다.

## 구현 파일

```text
src/recall_risk/serving/app.py
src/recall_risk/storage/postgres.py
tests/test_serving_app.py
```

## 구현한 endpoint

```text
GET /health
GET /health/db
GET /risk-scores/latest
```

지원 query parameter:

```text
limit: 1~100, default 25
make: optional exact match
model: optional exact match
component: optional partial match
```

예시:

```text
GET /risk-scores/latest?limit=10
GET /risk-scores/latest?limit=2&make=FORD
GET /risk-scores/latest?limit=2&make=FORD&component=ENGINE
```

## 실행 방법

PostgreSQL 실행:

```bash
docker compose up -d postgres
```

API 실행:

```bash
$env:PYTHONPATH='src'
uvicorn recall_risk.serving.app:app --reload --host 0.0.0.0 --port 8000
```

PowerShell 확인:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/db
Invoke-RestMethod "http://localhost:8000/risk-scores/latest?limit=3"
```

## 테스트 결과

단위 테스트:

```bash
$env:PYTHONPATH='src'
python -m pytest tests\test_serving_app.py -q
```

결과:

```text
2 passed
```

전체 테스트:

```bash
$env:PYTHONPATH='src'
python -m pytest -q
```

결과:

```text
3 passed, 1 warning
```

warning은 기존 `baseline_score.py`의 pandas `FutureWarning`이며 이번 FastAPI 작업과 직접 관련 없다.

## 실제 PostgreSQL smoke test

실행:

```text
GET /health
GET /health/db
GET /risk-scores/latest?limit=3
GET /risk-scores/latest?limit=2&make=FORD&component=ENGINE
```

결과:

```text
GET /health -> 200 {"status": "ok"}
GET /health/db -> 200 {"status": "ok", "database": "postgresql"}
GET /risk-scores/latest?limit=3 -> 200
GET /risk-scores/latest?limit=2&make=FORD&component=ENGINE -> 200
```

`limit=3` 응답 상위 결과:

| rank | make | model | model_year | component | week_start | score |
|---:|---|---|---:|---|---|---:|
| 1 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2.8062 |
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 2.4749 |
| 3 | FORD | ESCAPE | 2015 | POWER TRAIN | 2026-05-11 | 2.4749 |

`make=FORD&component=ENGINE` 응답 예:

| rank | make | model | model_year | component | week_start | score |
|---:|---|---|---:|---|---|---:|
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 2.4749 |
| 5 | FORD | EXPLORER | 2021 | ENGINE | 2026-05-11 | 2.4749 |

## 현재 의미

완료된 것:

```text
PostgreSQL 적재 결과를 API에서 조회
DB health check
query parameter 기반 필터링
단위 테스트
실제 DB smoke test
```

아직 안 한 것:

```text
API Dockerfile / compose service화
MLflow 모델/메트릭 관리
Airflow DAG orchestration
모델 재학습 자동화
```

## 결론

P2 FastAPI PostgreSQL 조회 API는 완료했다.

다음 작업은 **P3 MLflow 연결**이다.

