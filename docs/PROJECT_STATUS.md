# Project Status

작성일: 2026-05-23 KST

## 프로젝트

```text
Vehicle Recall Risk MLOps
```

## 목표

미국 NHTSA 공개 데이터를 이용해 차량/부품 단위의 리콜 위험 신호를 조기 감지하는 MVP를 만들고, 이후 MLOps 포트폴리오 구조로 확장한다.

## 현재 상태

```text
MVP complete
PostgreSQL load verified
FastAPI read API verified
MLflow baseline logging verified
Airflow DAG scaffold/smoke verified
Dockerized API verified
GitHub Actions CI added
```

## MVP 주요 결과

기준 run:

```text
20260515T114046Z
```

```text
unique vehicle-year count: 917
complaints rows: 103440
recalls rows: 3018
weekly feature rows: 1189569
label-ready rows: 1172332
positive rows: 4348
test positives: 1611
rule AP: 0.006281
logistic AP: 0.008251
latest risk week: 2026-05-11
```

## 기술스택 적용 상태

```text
PostgreSQL: done
FastAPI: done
MLflow: done
Airflow: smoke done
Docker API: done
GitHub Actions CI: done
```

## 주요 실행 포트

```text
PostgreSQL: localhost:55432
FastAPI container: http://localhost:28000
Airflow UI: http://localhost:18080
```

## 주요 결과 문서

```text
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
docs/AIRFLOW_DAG_RESULTS.md
docs/DOCKER_CI_RESULTS.md
```

## 현재 다음 작업 후보

이제 필수 MLOps scaffold는 한 사이클 완성했다.

다음부터는 둘 중 하나를 선택한다.

### A. 포트폴리오 정리

```text
README 정식 개편
아키텍처 다이어그램
docs/PORTFOLIO_BRIEF.md 작성
실행 방법 정리
한계와 개선 계획 정리
```

### B. 모델/데이터 품질 개선

```text
scikit-learn baseline 교체
feature 개선
component matching 개선
label 품질 개선
MLflow model artifact 정교화
```

## 선택 작업

Airflow 전체 DAG end-to-end 실행은 아직 하지 않았다.

```text
현재는 DAG import와 핵심 task smoke test로 orchestration scaffold를 검증했다.
전체 재실행은 시간 비용이 있으므로 별도 선택 작업으로 둔다.
```

