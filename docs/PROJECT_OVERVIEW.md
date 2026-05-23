# Project Overview

작성일: 2026-05-22 KST

## 한 줄 소개

미국 NHTSA 공개 데이터를 이용해 차량 리콜 위험 신호를 조기 감지하고, 이를 MLOps 파이프라인으로 운영화하는 프로젝트다.

## 프로젝트 목적

이 프로젝트의 목적은 단순히 ML 모델 하나를 만드는 것이 아니다.

백엔드 개발자가 MLOps 직무 전환을 설명할 수 있도록, 다음 흐름을 실제 코드와 로컬 인프라로 구성하는 것이 목표다.

```text
공개 API 데이터 수집
-> raw JSON 저장
-> 정규화
-> feature 생성
-> label 생성
-> baseline model 평가
-> PostgreSQL 적재
-> FastAPI 조회 API
-> MLflow 실험 추적
-> Airflow orchestration
```

## 문제 정의

NHTSA의 소비자 불만 데이터와 리콜 데이터를 이용해 다음 단위로 리콜 위험 신호를 본다.

```text
make / model / model_year / component / week
```

현재 label은 다음과 같다.

```text
해당 주차 이후 90일 안에 관련 recall이 발생하는가
```

현재 score는 보정된 리콜 확률이 아니다.

```text
complaint spike 기반 위험 신호 점수
```

## 현재 데이터 소스

초기 데이터 소스:

```text
US NHTSA
```

NHTSA를 먼저 선택한 이유:

```text
1. 공개 API 접근이 비교적 쉽다.
2. complaints / recalls / vehicle metadata가 연결 가능하다.
3. 미국 자동차 리콜 데이터는 포트폴리오 주제로 설명하기 쉽다.
4. 현대/기아 등 한국 제조사도 미국 시장 데이터에 포함된다.
```

향후 확장 후보:

```text
한국 자동차 리콜/안전 관련 공공 API
제조사 공지
소비자 커뮤니티/뉴스 신호
```

다만 MVP 단계에서는 US NHTSA만 사용한다.

## 현재 구현 상태

```text
MVP data/model cycle: done
PostgreSQL load: done
FastAPI read API: done
MLflow logging: done
Airflow DAG E2E: done
scikit-learn baseline: done
```

## 주요 결과

기준 run:

```text
20260515T114046Z
```

```text
vehicle-year candidates: 917
complaints rows: 103440
recalls rows: 3018
weekly feature rows: 1189569
label-ready rows: 1172332
positive rows: 4348
rule AP: 0.006281
logistic AP: 0.008191
latest risk week: 2026-05-11
```

## 현재 아키텍처

```text
NHTSA API
  -> pipeline scripts
  -> local CSV/JSON artifacts
  -> PostgreSQL
  -> FastAPI read API
  -> MLflow tracking
  -> Airflow DAG
```

## 포트폴리오에서 강조할 점

이 프로젝트는 현재 모델 성능 자체보다 다음 역량을 보여주는 데 초점을 둔다.

```text
데이터 수집 파이프라인 설계
feature/label 생성
불균형 binary event 문제 설정
baseline 평가
PostgreSQL 적재
API serving
실험 추적
workflow orchestration
문서화
```

## 관련 문서

```text
docs/PROJECT_STATUS.md
docs/BACKLOG.md
docs/MVP_SUMMARY.md
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
```
