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

try:
    from airflow.operators.trigger_dagrun import TriggerDagRunOperator
except ImportError:  # Airflow 3.x compatibility.
    from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator  # type: ignore


PROJECT_ROOT = os.getenv("PROJECT_ROOT", "/opt/airflow/project")
VEHICLE_MODELS_CSV = os.getenv(
    "NHTSA_COLLECT_VEHICLES_CSV",
    f"{PROJECT_ROOT}/configs/nhtsa_collection_vehicles.csv",
)
COLLECT_LIMIT = os.getenv("NHTSA_COLLECT_LIMIT", "5")
SLEEP_SECONDS = os.getenv("NHTSA_COLLECT_SLEEP_SECONDS", "0.2")
COLLECT_SCHEDULE = os.getenv("NHTSA_COLLECT_SCHEDULE", "@daily")
DEFAULT_DATA_AS_OF_DATE = os.getenv("NHTSA_DATA_AS_OF_DATE", "2026-05-15")

RUN_ID_TEMPLATE = "{{ dag_run.conf.get('run_id', 'collect_' ~ ts_nodash) }}"
DATA_AS_OF_DATE_TEMPLATE = "{{ dag_run.conf.get('data_as_of_date', params.data_as_of_date) }}"


def project_command(command: str) -> str:
    return f"cd {PROJECT_ROOT} && {command}"


default_args = {
    "owner": "recall-risk",
    "retries": 0,
}


with DAG(
    dag_id="nhtsa_collect_incremental",
    description=(
        "Scheduled NHTSA snapshot collector for selected vehicle-year targets. "
        "This stores raw JSON and a manifest for downstream processing."
    ),
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule=COLLECT_SCHEDULE,
    catchup=False,
    params={
        "data_as_of_date": DEFAULT_DATA_AS_OF_DATE,
    },
    tags=["nhtsa", "recall-risk", "collection", "snapshot"],
) as dag:
    check_collection_inputs = BashOperator(
        task_id="check_collection_inputs",
        bash_command=project_command(
            'test -f pipelines/collect_backfill.py '
            '&& test -f "$NHTSA_COLLECT_VEHICLES_CSV" '
            '&& echo "vehicle_models=$NHTSA_COLLECT_VEHICLES_CSV"'
        ),
        env={"NHTSA_COLLECT_VEHICLES_CSV": VEHICLE_MODELS_CSV},
        do_xcom_push=False,
    )

    collect_nhtsa_snapshot = BashOperator(
        task_id="collect_nhtsa_snapshot",
        bash_command=project_command(
            'python pipelines/collect_backfill.py '
            '--vehicle-models "$NHTSA_COLLECT_VEHICLES_CSV" '
            f'--run-id "{RUN_ID_TEMPLATE}" '
            "--limit \"{{ dag_run.conf.get('limit', params.collect_limit) }}\" "
            "--sleep-seconds \"{{ dag_run.conf.get('sleep_seconds', params.sleep_seconds) }}\""
        ),
        env={"NHTSA_COLLECT_VEHICLES_CSV": VEHICLE_MODELS_CSV},
        params={
            "collect_limit": COLLECT_LIMIT,
            "sleep_seconds": SLEEP_SECONDS,
        },
        do_xcom_push=False,
    )

    validate_manifest = BashOperator(
        task_id="validate_manifest",
        bash_command=project_command(
            f'manifest_path="data/raw/backfill/{RUN_ID_TEMPLATE}/manifest.csv"; '
            'test -s "$manifest_path"; '
            'manifest_rows=$(($(wc -l < "$manifest_path") - 1)); '
            'echo "manifest_rows=$manifest_rows"; '
            'test "$manifest_rows" -gt 0'
        ),
        do_xcom_push=False,
    )

    trigger_processing_dag = TriggerDagRunOperator(
        task_id="trigger_recall_risk_mvp",
        trigger_dag_id="nhtsa_recall_risk_mvp",
        trigger_run_id=f"process_{RUN_ID_TEMPLATE}",
        conf={
            "run_id": RUN_ID_TEMPLATE,
            "data_as_of_date": DATA_AS_OF_DATE_TEMPLATE,
            "triggered_by": "nhtsa_collect_incremental",
            "source_dag_run_id": "{{ dag_run.run_id }}",
        },
        wait_for_completion=False,
    )

    check_collection_inputs >> collect_nhtsa_snapshot >> validate_manifest >> trigger_processing_dag
