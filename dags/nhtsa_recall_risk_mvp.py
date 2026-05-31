from __future__ import annotations

import os
from datetime import datetime

try:
    from airflow import DAG
except ImportError:  # Airflow 3.x compatibility.
    from airflow.sdk import DAG  # type: ignore

try:
    from airflow.operators.bash import BashOperator
except ImportError:  # Airflow 3.x compatibility.
    from airflow.providers.standard.operators.bash import BashOperator  # type: ignore


PROJECT_ROOT = os.getenv("PROJECT_ROOT", "/opt/airflow/project")
DEFAULT_RUN_ID = os.getenv("NHTSA_RUN_ID", "20260515T114046Z")
DEFAULT_DATA_AS_OF_DATE = os.getenv("NHTSA_DATA_AS_OF_DATE", "2026-05-15")

RUN_ID_TEMPLATE = "{{ dag_run.conf.get('run_id', params.default_run_id) }}"
DATA_AS_OF_DATE_TEMPLATE = (
    "{{ dag_run.conf.get('data_as_of_date', params.default_data_as_of_date) }}"
)


def project_command(command: str) -> str:
    return f"cd {PROJECT_ROOT} && {command}"


default_args = {
    "owner": "recall-risk",
    "retries": 0,
}


with DAG(
    dag_id="nhtsa_recall_risk_mvp",
    description="Rebuild the NHTSA recall-risk MVP outputs and publish them to PostgreSQL/MLflow.",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule=None,
    catchup=False,
    params={
        "default_run_id": DEFAULT_RUN_ID,
        "default_data_as_of_date": DEFAULT_DATA_AS_OF_DATE,
    },
    tags=["nhtsa", "recall-risk", "mvp", "mlops"],
) as dag:
    check_project = BashOperator(
        task_id="check_project_files",
        bash_command=project_command(
            "test -f pipelines/normalize_backfill.py "
            "&& test -f pipelines/build_features_labels_backfill.py "
            "&& test -f pipelines/train_baseline_backfill.py "
            "&& test -f pipelines/load_postgres.py "
            "&& test -f pipelines/log_baseline_mlflow.py "
            f'&& test -s "data/raw/backfill/{RUN_ID_TEMPLATE}/manifest.csv" '
            f'&& echo "processing_run_id={RUN_ID_TEMPLATE}" '
            f'&& echo "data_as_of_date={DATA_AS_OF_DATE_TEMPLATE}"'
        ),
        do_xcom_push=False,
    )

    normalize_backfill = BashOperator(
        task_id="normalize_backfill",
        bash_command=project_command(
            f'python pipelines/normalize_backfill.py --run-id "{RUN_ID_TEMPLATE}"'
        ),
        do_xcom_push=False,
    )

    build_features_labels = BashOperator(
        task_id="build_features_labels",
        bash_command=project_command(
            "python pipelines/build_features_labels_backfill.py "
            f'--run-id "{RUN_ID_TEMPLATE}" '
            f'--data-as-of-date "{DATA_AS_OF_DATE_TEMPLATE}"'
        ),
        do_xcom_push=False,
    )

    train_baseline = BashOperator(
        task_id="train_baseline",
        bash_command=project_command(
            "python pipelines/train_baseline_backfill.py "
            f'--run-id "{RUN_ID_TEMPLATE}" '
            "--epochs 120 "
            "--negative-ratio 20 "
            "--max-train-rows 100000"
        ),
        do_xcom_push=False,
    )

    generate_latest_risk_report = BashOperator(
        task_id="generate_latest_risk_report",
        bash_command=project_command(
            f'python pipelines/generate_latest_risk_report.py --run-id "{RUN_ID_TEMPLATE}" --top-k 25'
        ),
        do_xcom_push=False,
    )

    load_postgres = BashOperator(
        task_id="load_postgres",
        bash_command=project_command(
            f'python pipelines/load_postgres.py --run-id "{RUN_ID_TEMPLATE}" --apply-schema'
        ),
        do_xcom_push=False,
    )

    log_mlflow = BashOperator(
        task_id="log_mlflow",
        bash_command=project_command(
            f'python pipelines/log_baseline_mlflow.py --run-id "{RUN_ID_TEMPLATE}"'
        ),
        do_xcom_push=False,
    )

    (
        check_project
        >> normalize_backfill
        >> build_features_labels
        >> train_baseline
        >> generate_latest_risk_report
        >> load_postgres
        >> log_mlflow
    )
