# Architecture Visualization

작성일: 2026-05-31 KST

## 1. 현재 아키텍처

현재 구조는 **수집 DAG**와 **처리/학습 DAG**가 분리되어 있다.

중요한 점:

```text
1. nhtsa_collect_incremental DAG는 live NHTSA API를 호출해서 raw snapshot을 만든다.
2. nhtsa_recall_risk_mvp DAG는 특정 NHTSA_RUN_ID를 기준으로 정규화/feature/학습/적재를 수행한다.
3. 두 DAG 사이의 자동 handoff는 아직 없다.
4. PostgreSQL은 serving용 결과 저장소 역할을 한다.
5. MLflow는 현재 SQLite tracking URI 기반으로 baseline run을 기록한다.
```

```mermaid
flowchart LR
    subgraph external["External data source"]
        nhtsa["NHTSA APIs<br/>complaints / recalls"]
    end

    subgraph airflow["Airflow"]
        scheduler["airflow-scheduler"]
        webserver["airflow-webserver"]

        subgraph collect_dag["DAG: nhtsa_collect_incremental<br/>schedule: @daily"]
            c1["check_collection_inputs"]
            c2["collect_nhtsa_snapshot<br/>pipelines/collect_backfill.py"]
            c3["validate_manifest"]
            c1 --> c2 --> c3
        end

        subgraph mvp_dag["DAG: nhtsa_recall_risk_mvp<br/>schedule: manual"]
            m1["check_project_files"]
            m2["normalize_backfill.py"]
            m3["build_features_labels_backfill.py"]
            m4["train_baseline_backfill.py<br/>scikit-learn"]
            m5["generate_latest_risk_report.py"]
            m6["load_postgres.py"]
            m7["log_baseline_mlflow.py"]
            m1 --> m2 --> m3 --> m4 --> m5 --> m6 --> m7
        end
    end

    subgraph files["Local project artifacts"]
        raw["data/raw/backfill/&lt;run_id&gt;<br/>raw JSON + manifest.csv"]
        interim["data/interim/backfill/&lt;run_id&gt;<br/>complaints.csv / recalls.csv"]
        processed["data/processed/backfill/&lt;run_id&gt;<br/>features / labels / predictions / risk scores"]
        reports["reports/*.md"]
        model_file["sklearn joblib artifact"]
        mlflow_file["mlflow_airflow.db<br/>local SQLite tracking"]
    end

    subgraph db["PostgreSQL: recall_risk"]
        t1["backfill_manifest"]
        t2["complaints / recalls"]
        t3["weekly_features"]
        t4["training_dataset"]
        t5["latest_risk_scores"]
        view["v_latest_risk_scores"]
    end

    subgraph serving["Serving"]
        api["FastAPI container<br/>src/recall_risk/serving/app.py"]
        client["User / Portfolio reviewer"]
    end

    subgraph ci["GitHub Actions CI"]
        tests["pytest"]
        dag_parse["DAG syntax check"]
        sample_e2e["offline sample E2E"]
        docker_build["docker compose build api"]
        api_smoke["PostgreSQL + API smoke"]
    end

    nhtsa --> c2
    c2 --> raw
    c3 --> raw

    raw --> m2
    m2 --> interim
    interim --> m3
    m3 --> processed
    m4 --> processed
    m4 --> model_file
    m5 --> reports
    m6 --> db
    m7 --> mlflow_file

    db --> view
    view --> api
    api --> client

    tests --> dag_parse --> sample_e2e --> docker_build --> api_smoke

    c3 -. "현재 자동 연결 없음<br/>run_id handoff pending" .-> m1

    classDef done fill:#e7f5ff,stroke:#1c7ed6,color:#102a43;
    classDef gap fill:#fff3bf,stroke:#f08c00,color:#3b2f00;
    classDef store fill:#ebfbee,stroke:#2b8a3e,color:#102a43;
    classDef serve fill:#f3f0ff,stroke:#7048e8,color:#102a43;

    class c1,c2,c3,m1,m2,m3,m4,m5,m6,m7,tests,dag_parse,sample_e2e,docker_build,api_smoke done;
    class raw,interim,processed,reports,model_file,mlflow_file,t1,t2,t3,t4,t5,view store;
    class api,client serve;
```

## 2. 현재 Airflow DAG 관점

현재 Airflow DAG는 두 개다.

```mermaid
flowchart TB
    subgraph collect["nhtsa_collect_incremental"]
        a["check_collection_inputs"]
        b["collect_nhtsa_snapshot"]
        c["validate_manifest"]
        a --> b --> c
    end

    subgraph process["nhtsa_recall_risk_mvp"]
        p0["check_project_files"]
        p1["normalize_backfill"]
        p2["build_features_labels"]
        p3["train_baseline"]
        p4["generate_latest_risk_report"]
        p5["load_postgres"]
        p6["log_mlflow"]
        p0 --> p1 --> p2 --> p3 --> p4 --> p5 --> p6
    end

    c -. "pending:<br/>TriggerDagRunOperator or Dataset scheduling" .-> p0
```

현재 문제는 `nhtsa_recall_risk_mvp`가 환경변수 `NHTSA_RUN_ID`에 고정된 run을 처리한다는 점이다.

```text
현재 기본값: 20260515T114046Z
수집 DAG 최신 산출물 예시: collect_20260525T171005
```

따라서 다음 개선의 첫 번째 핵심은 **수집 DAG가 만든 run_id를 처리 DAG에 전달**하는 것이다.

## 3. 앞으로 바뀌어야 하는 아키텍처: 1차 목표

가장 가까운 목표는 **DAG 간 handoff**다.

```mermaid
flowchart LR
    nhtsa["NHTSA APIs"] --> collect["nhtsa_collect_incremental<br/>daily snapshot collector"]
    collect --> raw["data/raw/backfill/&lt;generated_run_id&gt;"]
    collect --> manifest["manifest.csv<br/>run_id / endpoint / count / raw_path"]

    collect --> handoff["TriggerDagRunOperator<br/>or Airflow Dataset"]
    handoff --> process["nhtsa_recall_risk_mvp<br/>conf.run_id = generated_run_id"]

    process --> normalize["normalize_backfill"]
    normalize --> features["features + labels"]
    features --> train["train baseline / score"]
    train --> load["load_postgres"]
    train --> mlflow["log_mlflow"]
    load --> postgres["PostgreSQL serving tables"]
    postgres --> api["FastAPI"]

    classDef next fill:#fff3bf,stroke:#f08c00,color:#3b2f00;
    class handoff,process next;
```

필요 변경:

```text
1. nhtsa_recall_risk_mvp가 dag_run.conf["run_id"]를 받도록 수정
2. nhtsa_collect_incremental 마지막 task에서 처리 DAG trigger
3. 처리 DAG의 NHTSA_RUN_ID 고정값 의존 제거
4. run_id별 결과가 PostgreSQL에 적재될 때 metadata를 명확히 남김
```

## 4. 앞으로 바뀌어야 하는 아키텍처: 목표형 MLOps 구조

최종적으로는 CSV 중심 batch artifact 구조에서 **DB/state 중심 incremental MLOps 구조**로 이동해야 한다.

```mermaid
flowchart TB
    subgraph source["Sources"]
        complaints_api["NHTSA complaints API"]
        recalls_api["NHTSA recalls API"]
        vpic_api["VPIC vehicle/model API"]
        future_sources["later:<br/>investigations / manufacturer communications"]
    end

    subgraph orchestration["Airflow orchestration"]
        collect["daily collection DAG"]
        dq["data quality checks"]
        ingest["incremental ingestion DAG"]
        feature_job["feature generation DAG"]
        train_job["training DAG<br/>scheduled or manual"]
        score_job["batch scoring DAG"]
    end

    subgraph lake["Raw / replayable layer"]
        raw_json["raw JSON snapshots<br/>partitioned by run_id/date/source"]
        manifest["collection manifest"]
    end

    subgraph warehouse["PostgreSQL analytical/serving store"]
        ingest_state["ingestion_state<br/>source cursor / checksum / fetched_at"]
        raw_index["raw_record_index<br/>dedupe keys"]
        bronze["bronze normalized tables<br/>complaints / recalls"]
        silver["silver feature tables<br/>weekly_features"]
        labels["label tables<br/>next_90d_recall"]
        predictions["prediction tables<br/>batch scores by run/model_version"]
        serving_view["serving views<br/>v_latest_risk_scores"]
    end

    subgraph modelops["Model operations"]
        train["scikit-learn / later LightGBM"]
        registry["MLflow tracking + model registry"]
        eval["evaluation reports<br/>AP / recall@K / calibration"]
        promote["model promotion gate"]
    end

    subgraph serving["Serving / consumption"]
        fastapi["FastAPI"]
        dashboard["dashboard<br/>later"]
        alert["alerts<br/>later"]
    end

    subgraph monitoring["Monitoring"]
        data_monitor["data freshness / row counts"]
        drift_monitor["feature drift"]
        model_monitor["model quality by backtest window"]
        api_monitor["API health / latency"]
    end

    complaints_api --> collect
    recalls_api --> collect
    vpic_api --> collect
    future_sources -. later .-> collect

    collect --> raw_json
    collect --> manifest
    manifest --> dq
    raw_json --> dq
    dq --> ingest
    ingest --> ingest_state
    ingest --> raw_index
    ingest --> bronze
    bronze --> feature_job
    feature_job --> silver
    bronze --> labels
    silver --> train_job
    labels --> train_job
    train_job --> train
    train --> registry
    train --> eval
    eval --> promote
    promote --> score_job
    silver --> score_job
    registry --> score_job
    score_job --> predictions
    predictions --> serving_view
    serving_view --> fastapi
    serving_view --> dashboard
    serving_view --> alert

    manifest --> data_monitor
    bronze --> data_monitor
    silver --> drift_monitor
    predictions --> model_monitor
    fastapi --> api_monitor

    classDef target fill:#e7f5ff,stroke:#1c7ed6,color:#102a43;
    classDef storage fill:#ebfbee,stroke:#2b8a3e,color:#102a43;
    classDef later fill:#f3f0ff,stroke:#7048e8,color:#102a43;
    classDef monitor fill:#fff3bf,stroke:#f08c00,color:#3b2f00;

    class collect,dq,ingest,feature_job,train_job,score_job,train,registry,eval,promote target;
    class raw_json,manifest,ingest_state,raw_index,bronze,silver,labels,predictions,serving_view storage;
    class dashboard,alert,future_sources later;
    class data_monitor,drift_monitor,model_monitor,api_monitor monitor;
```

## 5. 현재에서 목표로 가는 단계

```mermaid
flowchart LR
    s0["현재<br/>수집 DAG와 처리 DAG 분리<br/>manual handoff"]
    s1["Step 1<br/>run_id conf 전달<br/>collection -> processing trigger"]
    s2["Step 2<br/>PostgreSQL ingestion_state<br/>record-level dedupe"]
    s3["Step 3<br/>training/scoring 분리<br/>model_version 기록"]
    s4["Step 4<br/>MLflow registry + promotion gate"]
    s5["Step 5<br/>monitoring / dashboard / alerts"]

    s0 --> s1 --> s2 --> s3 --> s4 --> s5
```

우선순위:

| Priority | Change | Why |
|---:|---|---|
| 1 | `dag_run.conf["run_id"]` 기반 처리 DAG 실행 | 수집과 처리 사이의 실제 자동화 연결 |
| 2 | `TriggerDagRunOperator` 또는 Airflow Dataset 적용 | daily collection 이후 자동 후속 처리 |
| 3 | ingestion state/dedupe table 추가 | snapshot 반복 수집에서 true incremental ingestion으로 전환 |
| 4 | prediction/model_version metadata 추가 | 포트폴리오에서 MLOps maturity를 설명 가능 |
| 5 | monitoring 최소 지표 추가 | 운영형 프로젝트로 확장 |

## 6. 한 줄 판단

현재는 다음 상태다.

```text
Airflow + PostgreSQL + FastAPI + MLflow + CI는 붙었다.
하지만 collection과 processing은 아직 자동 연결되지 않았다.
그리고 incremental ingestion은 아직 snapshot collector 수준이다.
```

다음 구현은 다음 하나가 맞다.

```text
nhtsa_recall_risk_mvp를 dag_run.conf["run_id"] 기반으로 바꾸고,
nhtsa_collect_incremental이 성공하면 그 run_id로 처리 DAG를 trigger하게 만든다.
```
