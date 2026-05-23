# Backlog

MVP와 MLOps scaffold는 end-to-end로 한 사이클 완료했다.

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
P5 Docker/CI 정리: done
P6 Airflow 전체 DAG E2E 실행: done
P7 포트폴리오 브리프/로컬 실행 가이드: done
```

## 완료된 MLOps 포트폴리오화 작업

| ID | 작업 | 목적 | 상태 |
|---|---|---|---|
| P1 | PostgreSQL 적재 확인 | CSV 결과물을 DB 테이블로 적재 | done |
| P2 | FastAPI에서 PostgreSQL 조회 | latest risk score API | done |
| P3 | MLflow 연결 | baseline metrics/model artifact 관리 | done |
| P4 | Airflow DAG 전환 | pipeline orchestration scaffold/smoke | done |
| P5 | Docker/CI 정리 | 실행성과 자동 검증 강화 | done |
| P6 | Airflow 전체 DAG E2E 실행 | orchestration end-to-end 검증 | done |
| P7 | 포트폴리오 브리프/로컬 실행 가이드 | 공개 설명 자료와 재실행 절차 정리 | done |

## 다음 작업 후보

### Q1. 포트폴리오 정리

목표:

```text
채용 담당자/면접관이 빠르게 이해할 수 있는 공개용 설명 자료를 만든다.
```

작업:

```text
README 정식 개편: pending
docs/PORTFOLIO_BRIEF.md 작성: done
docs/RUNBOOK.md 작성: done
Mermaid 아키텍처 다이어그램 추가: done
실행 순서 정리: done
기술적 tradeoff 정리: done
```

### Q2. 모델 품질 개선

목표:

```text
현재 pure Python baseline을 더 일반적인 ML workflow로 개선한다.
```

작업:

```text
scikit-learn LogisticRegression baseline
sklearn Pipeline + StandardScaler
class_weight='balanced'
joblib artifact 저장
MLflow sklearn model logging
```

### Q3. 데이터/label 품질 개선

목표:

```text
recall matching과 component normalization 품질을 개선한다.
```

작업:

```text
component mapping 개선
make/model alias 개선
future-dated recall handling 추가 검증
investigations/manufacturer communications 추가 검토
```

## 남은 주의사항

```text
1. collect_backfill은 이번 Airflow E2E DAG에 포함하지 않았다.
2. 현재 Airflow E2E는 기존 raw backfill 데이터를 기준으로 재처리한다.
3. GitHub Actions 원격 실행 green 여부는 GitHub에서 별도 확인이 필요하다.
```
