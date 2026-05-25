from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "20260515T114046Z"
SCHEMA_PATH = PROJECT_ROOT / "infra" / "postgres" / "initdb" / "001_schema.sql"


TABLE_LOADS = [
    (
        "recall_risk.backfill_manifest",
        PROJECT_ROOT / "data" / "raw" / "backfill" / DEFAULT_RUN_ID / "manifest.csv",
    ),
    (
        "recall_risk.complaints",
        PROJECT_ROOT / "data" / "interim" / "backfill" / DEFAULT_RUN_ID / "complaints.csv",
    ),
    (
        "recall_risk.recalls",
        PROJECT_ROOT / "data" / "interim" / "backfill" / DEFAULT_RUN_ID / "recalls.csv",
    ),
    (
        "recall_risk.weekly_features",
        PROJECT_ROOT / "data" / "processed" / "backfill" / DEFAULT_RUN_ID / "weekly_features.csv",
    ),
    (
        "recall_risk.training_dataset",
        PROJECT_ROOT / "data" / "processed" / "backfill" / DEFAULT_RUN_ID / "training_dataset.csv",
    ),
    (
        "recall_risk.training_dataset_labeled_only",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "backfill"
        / DEFAULT_RUN_ID
        / "training_dataset_labeled_only.csv",
    ),
    (
        "recall_risk.latest_risk_scores",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "backfill"
        / DEFAULT_RUN_ID
        / "latest_risk_scores.csv",
    ),
    (
        "recall_risk.baseline_test_predictions",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "backfill"
        / DEFAULT_RUN_ID
        / "baseline_test_predictions.csv",
    ),
    (
        "recall_risk.baseline_logistic_coefficients",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "backfill"
        / DEFAULT_RUN_ID
        / "baseline_logistic_coefficients.csv",
    ),
]


SMOKE_TEST_TABLE_LOADS = [
    (
        "recall_risk.complaints",
        PROJECT_ROOT / "data" / "interim" / "smoke_test" / "ci_fixture" / "complaints.csv",
    ),
    (
        "recall_risk.recalls",
        PROJECT_ROOT / "data" / "interim" / "smoke_test" / "ci_fixture" / "recalls.csv",
    ),
    (
        "recall_risk.weekly_features",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "weekly_features.csv",
    ),
    (
        "recall_risk.training_dataset",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "training_dataset.csv",
    ),
    (
        "recall_risk.training_dataset_labeled_only",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "training_dataset_labeled_only.csv",
    ),
    (
        "recall_risk.latest_risk_scores",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "latest_risk_scores.csv",
    ),
    (
        "recall_risk.baseline_test_predictions",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "baseline_predictions.csv",
    ),
    (
        "recall_risk.baseline_logistic_coefficients",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "smoke_test"
        / "ci_fixture"
        / "baseline_logistic_coefficients.csv",
    ),
]


ALL_TABLES = [
    "recall_risk.backfill_manifest",
    "recall_risk.complaints",
    "recall_risk.recalls",
    "recall_risk.weekly_features",
    "recall_risk.training_dataset",
    "recall_risk.training_dataset_labeled_only",
    "recall_risk.latest_risk_scores",
    "recall_risk.baseline_test_predictions",
    "recall_risk.baseline_logistic_coefficients",
]


def import_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit(
            "psycopg is not installed. Install project dependencies first, e.g. "
            "`pip install -e .` or install `psycopg[binary]`."
        ) from exc
    return psycopg


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def table_loads_for_run(run_id: str, dataset: str = "backfill") -> list[tuple[str, Path]]:
    if dataset == "backfill":
        return [
            (table, Path(str(path).replace(DEFAULT_RUN_ID, run_id)))
            for table, path in TABLE_LOADS
        ]

    if dataset == "smoke_test":
        return [
            (table, Path(str(path).replace("ci_fixture", run_id)))
            for table, path in SMOKE_TEST_TABLE_LOADS
        ]

    raise ValueError(f"Unsupported dataset: {dataset}")


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://recall_user:recall_password@localhost:55432/recall_risk",
    )


def apply_schema(conn, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def truncate_tables(conn, table_names: list[str]) -> None:
    with conn.cursor() as cur:
        for table_name in table_names:
            cur.execute(f"TRUNCATE TABLE {table_name};")
    conn.commit()


def copy_csv(conn, table_name: str, csv_path: Path) -> int:
    if not csv_path.exists():
        print(f"SKIP missing file: {display_path(csv_path)}")
        return 0

    # Count data rows for reporting. This is cheap enough for MVP-sized CSVs.
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        row_count = max(0, sum(1 for _ in f) - 1)

    with conn.cursor() as cur:
        with csv_path.open("rb") as f:
            with cur.copy(f"COPY {table_name} FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
                while data := f.read(1024 * 1024):
                    copy.write(data)
    conn.commit()
    return row_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load MVP CSV outputs into PostgreSQL.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--dataset",
        choices=["backfill", "smoke_test"],
        default="backfill",
        help="CSV output family to load. Defaults to full backfill MVP outputs.",
    )
    parser.add_argument("--schema-path", default=str(SCHEMA_PATH))
    parser.add_argument("--apply-schema", action="store_true")
    parser.add_argument("--truncate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    psycopg = import_psycopg()
    loads = table_loads_for_run(args.run_id, args.dataset)

    print(f"Connecting to: {database_url()}")
    with psycopg.connect(database_url()) as conn:
        if args.apply_schema:
            print(f"Applying schema: {display_path(Path(args.schema_path))}")
            apply_schema(conn, Path(args.schema_path))

        if args.truncate:
            print("Truncating target tables...")
            truncate_tables(conn, ALL_TABLES)

        for table_name, csv_path in loads:
            print(f"Loading {display_path(csv_path)} -> {table_name}")
            row_count = copy_csv(conn, table_name, csv_path)
            print(f"  rows={row_count}")

    print("PostgreSQL load complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
