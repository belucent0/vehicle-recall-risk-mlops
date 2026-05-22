# Backlog

MVP는 완료했다. 현재는 MLOps 포트폴리오화 단계다.

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
P4 Airflow DAG scaffold/smoke: done
```

## 현재 다음 작업

```text
P5. Docker/CI 정리
```

목표:

```text
로컬 Python 실행 의존도를 줄이고, GitHub에서 최소 테스트가 자동으로 돌게 만든다.
```

산출물:

```text
infra/api/Dockerfile
docker-compose.yml api service
.github/workflows/ci.yml
docs/DOCKER_CI_RESULTS.md
```

## MLOps 포트폴리오화 작업

| ID | 작업 | 목적 | 상태 |
|---|---|---|---|
| P1 | PostgreSQL 적재 확인 | CSV 결과물을 DB 테이블로 적재 | done |
| P2 | FastAPI에서 PostgreSQL 조회 | latest risk score API | done |
| P3 | MLflow 연결 | baseline metrics/model artifact 관리 | done |
| P4 | Airflow DAG 전환 | pipeline orchestration scaffold/smoke | done |
| P5 | Docker/CI 정리 | 실행성과 자동 검증 강화 | next |

## P5 구현 메모

권장 범위:

```text
1. FastAPI용 Dockerfile 작성
2. docker-compose api 서비스 추가
3. /health, /risk-scores/latest smoke test
4. GitHub Actions에서 pytest 실행
5. 문서화
```

이번 단계에서 하지 않을 것:

```text
production-grade image optimization
multi-stage build 고도화
container registry push
배포 환경 구성
```

## 선택 작업

Airflow 전체 DAG 실행은 아직 하지 않았다.

이유:

```text
normalize/build/train/load 전체 재실행은 상대적으로 무거운 검증이다.
현재는 DAG import와 핵심 task smoke test로 orchestration scaffold를 검증했다.
```

필요하면 다음 명령으로 별도 실행한다.

```bash
docker compose exec airflow-webserver airflow dags unpause nhtsa_recall_risk_mvp
docker compose exec airflow-webserver airflow dags trigger nhtsa_recall_risk_mvp
```

