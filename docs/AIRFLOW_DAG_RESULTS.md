# Airflow DAG Results

작성일: 2026-05-22 KST

## 목적

기존 pipeline script들을 Airflow DAG로 묶어 orchestration 가능한 형태로 만든다.

이번 단계의 목표는 전체 대용량 DAG를 끝까지 재실행하는 것이 아니라, 다음을 확인하는 것이다.

```text
Airflow 이미지 빌드
metadata DB 초기화
webserver/scheduler 실행
DAG import
task dependency 구조 확인
가벼운 task smoke test
MLflow logging task smoke test
```

## 구현 파일

```text
docker-compose.yml
dags/nhtsa_recall_risk_mvp.py
infra/airflow/Dockerfile
infra/airflow/requirements.txt
```

## 구성

Airflow 서비스:

```text
airflow-postgres
airflow-init
airflow-webserver
airflow-scheduler
```

Airflow UI:

```text
http://localhost:18080
```

기본 계정:

```text
admin / admin
```

Airflow 컨테이너 내부 주요 버전:

```text
airflow 2.11.0
mlflow 2.22.5
pandas 2.1.4
protobuf 4.25.9
```

MLflow tracking URI:

```text
sqlite:////opt/airflow/project/mlflow_airflow.db
```

Airflow에서 사용하는 MLflow DB는 로컬 개발 중 생성한 `mlflow.db`와 분리했다. 로컬 MLflow 버전과 Airflow 이미지 내부 MLflow 버전 차이로 인한 SQLite schema 충돌을 피하기 위한 결정이다.

## 실행한 명령

### Compose/DAG 문법 확인

```bash
docker compose config --quiet
python -m py_compile dags\nhtsa_recall_risk_mvp.py
```

결과:

```text
passed
```

### Airflow 이미지 빌드

```bash
docker compose build --no-cache airflow-init airflow-webserver airflow-scheduler
```

결과:

```text
image: nhtsa-recall-risk-airflow:local
build: success
```

처음 빌드에서는 최신 MLflow 계열 의존성이 Airflow provider dependency와 충돌했다. 이후 `infra/airflow/requirements.txt`를 줄이고 `protobuf<5`를 추가해 최종 빌드에서는 dependency conflict warning 없이 통과했다.

### Airflow metadata DB 초기화

```bash
docker compose up airflow-init
```

결과:

```text
Database migrating done
User "admin" created with role "Admin"
exit code 0
```

### Airflow webserver/scheduler 실행

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

결과:

```text
airflow-webserver: healthy
airflow-scheduler: running
airflow-postgres: healthy
postgres: healthy
```

Health endpoint:

```text
GET http://localhost:18080/health
```

응답 요약:

```text
metadatabase: healthy
scheduler: healthy
```

## DAG 인식 확인

명령:

```bash
docker compose exec airflow-webserver airflow dags list
```

결과:

```text
dag_id: nhtsa_recall_risk_mvp
fileloc: /opt/airflow/dags/nhtsa_recall_risk_mvp.py
owner: recall-risk
is_paused: True
```

Task tree:

```text
check_project_files
  -> normalize_backfill
    -> build_features_labels
      -> train_baseline
        -> generate_latest_risk_report
          -> load_postgres
            -> log_mlflow
```

## Task smoke test

### check_project_files

명령:

```bash
docker compose exec airflow-webserver airflow tasks test nhtsa_recall_risk_mvp check_project_files 2026-05-22
```

결과:

```text
SUCCESS
```

확인한 파일:

```text
pipelines/normalize_backfill.py
pipelines/build_features_labels_backfill.py
pipelines/train_baseline_backfill.py
pipelines/load_postgres.py
pipelines/log_baseline_mlflow.py
```

### log_mlflow

명령:

```bash
docker compose exec airflow-webserver airflow tasks test nhtsa_recall_risk_mvp log_mlflow 2026-05-22
```

초기 결과:

```text
pipeline command 자체는 return code 0
그러나 BashOperator의 XCom push 단계에서 실패
```

원인:

```text
airflow tasks test의 temporary DAG run에서 BashOperator stdout을 XCom으로 push하려다
DAG run not found 오류 발생
```

수정:

```text
모든 BashOperator에 do_xcom_push=False 추가
```

재실행 결과:

```text
SUCCESS
MLflow run ID: 566fbae020ed4f729d40d285828539c5
```

## 현재 DAG의 의미

완료된 것:

```text
Airflow 컨테이너 구성
Airflow metadata DB 초기화
Airflow webserver/scheduler 실행
DAG import 확인
Task dependency 확인
가벼운 task smoke test
MLflow logging task smoke test
```

아직 안 한 것:

```text
전체 DAG end-to-end 실행
normalize/build/train/load 전체 task 실행 시간 측정
실패 task retry 정책 정교화
Airflow secrets/connection 정리
```

## 결론

P4 Airflow DAG 전환은 **scaffold와 smoke test 기준으로 완료**했다.

전체 DAG 재실행은 비용이 더 큰 검증이므로 별도 선택 작업으로 남긴다.

다음 주요 작업은 **P5 Docker/CI 정리**다.

