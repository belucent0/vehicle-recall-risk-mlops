# Backlog

MVP는 완료했다. 이제 MLOps 포트폴리오화 단계로 넘어간다.

## 기술스택 결정

2026-05-16 결정:

```text
PostgreSQL을 메인 저장소로 사용한다.
DuckDB는 도입하지 않는다.
```

2026-05-20:

```text
FastAPI를 붙여 PostgreSQL의 latest risk score를 읽는 API까지 확인했다.
```

2026-05-21:

```text
MLflow SQLite tracking backend에 baseline metrics/artifacts를 기록했다.
```

## 현재 완료 상태

```text
S0 프로젝트 구조 생성: done
S1 NHTSA API smoke test: done
S2 Raw JSON 정규화: done
S3 Weekly feature 생성: done
S4 90일 recall label 생성: done
S5 Baseline model 평가: done
M1 VPIC vehicle model list 수집: done
M2 모델명 alias/정규화 확인: done
M3 Backfill collector 구현: done
M4 Backfill 대상 vehicle model 후보 정제: done
M5 MVP 후보 vehicle backfill 수집 실행: done
M6 Backfill 정규화: done
M7 Backfill feature/label 생성: done
M8 Backfill baseline 재평가: done
M9 최신 risk score 리포트 생성: done
M10 MVP README 정리: done
P1 PostgreSQL 적재 확인: done
P2 FastAPI에서 PostgreSQL 조회: done
P3 MLflow 연결: done
```

## 현재 다음 작업

```text
P4. Airflow DAG 전환
```

목표:

```text
기존 pipeline script들을 Airflow DAG에서 실행 가능한 형태로 묶는다.
```

산출물:

```text
dags/nhtsa_recall_risk_mvp.py
docker-compose.yml Airflow 서비스 추가
Airflow 실행 문서
DAG smoke test 결과 문서
```

## MLOps 포트폴리오화 남은 작업

| ID | 작업 | 목적 | 상태 |
|---|---|---|---|
| P1 | PostgreSQL 적재 확인 | CSV 결과물을 DB 테이블로 적재 | done |
| P2 | FastAPI에서 PostgreSQL 조회 | latest risk score API | done |
| P3 | MLflow 연결 | baseline metrics/model artifact 관리 | done |
| P4 | Airflow DAG 전환 | 수집/정규화/feature/model pipeline orchestration | next |
| P5 | Docker/CI 정리 | 포트폴리오 실행성 강화 | pending |

## P4 구현 메모

Airflow는 처음부터 복잡하게 가지 않는다.

권장 범위:

```text
1. docker-compose에 airflow-webserver, airflow-scheduler 추가
2. dags/ 디렉터리 생성
3. 기존 Python pipeline script를 BashOperator로 호출
4. smoke용 DAG와 MVP backfill용 DAG를 분리할지 검토
5. PostgreSQL 적재와 MLflow logging task까지 DAG에 포함
```

이번 단계에서 하지 않을 것:

```text
KubernetesExecutor
CeleryExecutor
복잡한 retry/alert 정책
대규모 backfill scheduling
production-grade secrets manager
```

