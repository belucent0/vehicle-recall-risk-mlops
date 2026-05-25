# Docker / CI Results

작성일: 2026-05-26 KST

## 목적

FastAPI를 로컬 Python 실행이 아니라 Docker 컨테이너로 실행 가능하게 만들고, GitHub Actions에서 최소 테스트가 자동으로 실행되도록 한다.

이번 단계는 production 배포가 아니다. 포트폴리오 실행성과 기본 자동 검증을 갖추는 단계다.

## 구현 파일

```text
infra/api/Dockerfile
infra/api/requirements.txt
docker-compose.yml
.github/workflows/ci.yml
.env.example
.dockerignore
```

관련 수정:

```text
pyproject.toml
src/recall_risk/serving/app.py
.gitignore
```

`.dockerignore`를 추가해 `data/`, `logs/`, `mlflow*.db`, `models/`, `reports/` 같은 런타임 산출물이 Docker build context에 들어가지 않도록 했다.

## FastAPI Docker 구성

이미지:

```text
vehicle-recall-risk-api:local
```

컨테이너:

```text
vehicle-recall-risk-api
```

내부 포트:

```text
8000
```

로컬 호스트 포트:

```text
28000
```

처음에는 8000, 18000을 검토했지만 로컬 환경에서 이미 사용 중이었다. 따라서 기본값을 28000으로 정했다.

필요하면 `.env`에서 바꿀 수 있다.

```text
API_PORT=8000
```

## 실행 명령

빌드:

```bash
docker compose build api
```

실행:

```bash
docker compose up -d api
```

상태 확인:

```bash
docker compose ps api
```

## Smoke test 결과

실행:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:28000/health
Invoke-WebRequest -UseBasicParsing http://localhost:28000/health/db
Invoke-WebRequest -UseBasicParsing "http://localhost:28000/risk-scores/latest?limit=3"
```

결과:

```text
api container: healthy
GET /health: 200
GET /health/db: 200
GET /risk-scores/latest?limit=3: 200
```

상위 응답 예:

| rank | make | model | model_year | component | week_start | score |
|---:|---|---|---:|---|---|---:|
| 1 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2.8062 |
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 2.4749 |
| 3 | FORD | ESCAPE | 2015 | POWER TRAIN | 2026-05-11 | 2.4749 |

## CI 구성

파일:

```text
.github/workflows/ci.yml
```

Trigger:

```text
push to main
pull_request to main
```

실행 내용:

```text
actions/checkout@v4
actions/setup-python@v5
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
python pipelines/run_smoke_e2e.py --run-id ci_fixture --top-k 5 --max-iter 1000
docker compose build api
docker compose up -d postgres
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
docker compose up -d api
curl http://localhost:28000/health/db
curl "http://localhost:28000/risk-scores/latest?limit=3"
```

로컬에서 동일 설치 명령 검증:

```bash
python -m pip install -e ".[dev]"
```

결과:

```text
success
```

로컬 테스트:

```bash
python -m pytest -q
```

결과:

```text
4 passed, 1 warning
```

warning은 기존 pandas `FutureWarning`이며 이번 Docker/CI 작업과 직접 관련 없다.

원격 GitHub Actions 검증:

```text
workflow: CI
run: 26410440597
conclusion: success
```

## 현재 의미

완료된 것:

```text
FastAPI Dockerfile 추가
docker-compose api service 추가
API 컨테이너 build 성공
API 컨테이너 smoke test 성공
GitHub Actions CI 추가
editable install 검증
pytest 검증
offline sample E2E 검증
CI에서 API Docker build 검증
CI에서 sample PostgreSQL load 검증
CI에서 FastAPI DB/API smoke test 검증
```

아직 안 한 것:

```text
Docker image multi-stage 최적화
container registry push
API service production 배포
sample E2E의 Airflow DAG화
sample E2E의 MLflow logging 추가
```

## 결론

P5 Docker/CI 정리는 MVP 기준으로 완료했고, 이후 clean clone sample E2E와 API smoke test까지 CI에 추가했다.

다음 단계는 sample E2E를 Airflow/MLflow까지 확장하거나, 신규 데이터 수집 incremental DAG를 분리하는 것이다.
