from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


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

STATE_TABLES = [
    "recall_risk.raw_record_index",
    "recall_risk.ingestion_state",
]

METADATA_COLUMNS = ["load_run_id", "loaded_at_utc", "record_hash"]

RAW_RECORD_INDEX_TABLES = {
    "recall_risk.backfill_manifest",
    "recall_risk.complaints",
    "recall_risk.recalls",
}


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


def split_table_name(table_name: str) -> tuple[str, str]:
    parts = table_name.split(".", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Expected schema-qualified table name: {table_name}")
    return parts[0], parts[1]


def table_identifier(table_name: str):
    from psycopg import sql

    schema, name = split_table_name(table_name)
    return sql.Identifier(schema, name)


def column_identifiers(column_names: list[str]):
    from psycopg import sql

    return sql.SQL(", ").join(sql.Identifier(column_name) for column_name in column_names)


def truncate_tables(conn, table_names: list[str]) -> None:
    with conn.cursor() as cur:
        for table_name in table_names:
            cur.execute(f"TRUNCATE TABLE {table_name};")
    conn.commit()


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def row_hash(row: dict[str, str], headers: list[str]) -> str:
    payload = "\x1f".join(f"{header}={row.get(header, '') or ''}" for header in headers)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_augmented_csv(
    *,
    table_name: str,
    csv_path: Path,
    load_run_id: str,
    loaded_at_utc: str,
) -> tuple[Path, list[str], int]:
    with csv_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {display_path(csv_path)}")

        csv_headers = [
            header for header in reader.fieldnames
            if header not in METADATA_COLUMNS
        ]
        output_columns = csv_headers + METADATA_COLUMNS

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            suffix=".csv",
            prefix=f"load_{table_name.replace('.', '_')}_",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer = csv.DictWriter(temp_file, fieldnames=output_columns, lineterminator="\n")
            writer.writeheader()

            row_count = 0
            for row in reader:
                output_row = {header: row.get(header, "") or "" for header in csv_headers}
                output_row["load_run_id"] = load_run_id
                output_row["loaded_at_utc"] = loaded_at_utc
                output_row["record_hash"] = row_hash(output_row, csv_headers)
                writer.writerow(output_row)
                row_count += 1

    return temp_path, output_columns, row_count


def mark_ingestion_running(
    conn,
    *,
    table_name: str,
    load_run_id: str,
    dataset: str,
    source_path: Path,
    row_count: int,
    started_at_utc: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO recall_risk.ingestion_state (
                table_name,
                load_run_id,
                dataset,
                source_path,
                status,
                row_count,
                inserted_count,
                skipped_count,
                started_at_utc,
                completed_at_utc
            )
            VALUES (%s, %s, %s, %s, 'running', %s, NULL, NULL, %s, NULL)
            ON CONFLICT (table_name, load_run_id)
            DO UPDATE SET
                dataset = EXCLUDED.dataset,
                source_path = EXCLUDED.source_path,
                status = 'running',
                row_count = EXCLUDED.row_count,
                inserted_count = NULL,
                skipped_count = NULL,
                started_at_utc = EXCLUDED.started_at_utc,
                completed_at_utc = NULL
            """,
            (
                table_name,
                load_run_id,
                dataset,
                display_path(source_path),
                str(row_count),
                started_at_utc,
            ),
        )
    conn.commit()


def mark_ingestion_finished(
    conn,
    *,
    table_name: str,
    load_run_id: str,
    status: str,
    row_count: int,
    inserted_count: int,
    completed_at_utc: str,
) -> None:
    skipped_count = max(0, row_count - inserted_count)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE recall_risk.ingestion_state
            SET
                status = %s,
                row_count = %s,
                inserted_count = %s,
                skipped_count = %s,
                completed_at_utc = %s
            WHERE table_name = %s
              AND load_run_id = %s
            """,
            (
                status,
                str(row_count),
                str(inserted_count),
                str(skipped_count),
                completed_at_utc,
                table_name,
                load_run_id,
            ),
        )
    conn.commit()


def update_raw_record_index(
    conn,
    *,
    temp_table_name: str,
    table_name: str,
    load_run_id: str,
    loaded_at_utc: str,
) -> None:
    from psycopg import sql

    statement = sql.SQL(
        """
        INSERT INTO recall_risk.raw_record_index (
            table_name,
            record_hash,
            first_seen_run_id,
            last_seen_run_id,
            seen_count,
            first_seen_at_utc,
            last_seen_at_utc
        )
        SELECT
            %(table_name)s,
            record_hash,
            %(load_run_id)s,
            %(load_run_id)s,
            1,
            %(loaded_at_utc)s,
            %(loaded_at_utc)s
        FROM (
            SELECT DISTINCT record_hash
            FROM {temp_table}
            WHERE record_hash IS NOT NULL
              AND record_hash <> ''
        ) AS records
        ON CONFLICT (table_name, record_hash)
        DO UPDATE SET
            last_seen_run_id = EXCLUDED.last_seen_run_id,
            seen_count = recall_risk.raw_record_index.seen_count + 1,
            last_seen_at_utc = EXCLUDED.last_seen_at_utc
        """
    ).format(temp_table=sql.Identifier(temp_table_name))

    with conn.cursor() as cur:
        cur.execute(
            statement,
            {
                "table_name": table_name,
                "load_run_id": load_run_id,
                "loaded_at_utc": loaded_at_utc,
            },
        )


def successful_ingestion_result(
    conn,
    *,
    table_name: str,
    load_run_id: str,
) -> dict[str, int] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT row_count, inserted_count, skipped_count
            FROM recall_risk.ingestion_state
            WHERE table_name = %s
              AND load_run_id = %s
              AND status = 'success'
            """,
            (table_name, load_run_id),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "rows": int(row[0] or 0),
        "inserted": int(row[1] or 0),
        "skipped": int(row[2] or 0),
    }


def copy_csv(
    conn,
    table_name: str,
    csv_path: Path,
    *,
    load_run_id: str,
    dataset: str,
) -> dict[str, int]:
    if not csv_path.exists():
        print(f"SKIP missing file: {display_path(csv_path)}")
        return {"rows": 0, "inserted": 0, "skipped": 0}

    previous_result = successful_ingestion_result(
        conn,
        table_name=table_name,
        load_run_id=load_run_id,
    )
    if previous_result is not None:
        print(f"  SKIP already ingested: table={table_name} run_id={load_run_id}")
        return previous_result

    from psycopg import sql

    loaded_at_utc = now_utc()
    temp_csv_path, copy_columns, row_count = build_augmented_csv(
        table_name=table_name,
        csv_path=csv_path,
        load_run_id=load_run_id,
        loaded_at_utc=loaded_at_utc,
    )
    temp_table_name = f"tmp_load_{uuid4().hex}"
    mark_ingestion_running(
        conn,
        table_name=table_name,
        load_run_id=load_run_id,
        dataset=dataset,
        source_path=csv_path,
        row_count=row_count,
        started_at_utc=loaded_at_utc,
    )

    inserted_count = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                    sql.Identifier(temp_table_name),
                    table_identifier(table_name),
                )
            )

            copy_statement = sql.SQL(
                "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)"
            ).format(
                sql.Identifier(temp_table_name),
                column_identifiers(copy_columns),
            )
            with temp_csv_path.open("rb") as f:
                with cur.copy(copy_statement) as copy:
                    while data := f.read(1024 * 1024):
                        copy.write(data)

            insert_statement = sql.SQL(
                "INSERT INTO {} ({}) SELECT {} FROM {} ON CONFLICT DO NOTHING"
            ).format(
                table_identifier(table_name),
                column_identifiers(copy_columns),
                column_identifiers(copy_columns),
                sql.Identifier(temp_table_name),
            )
            cur.execute(insert_statement)
            inserted_count = max(0, cur.rowcount)

            if table_name in RAW_RECORD_INDEX_TABLES:
                update_raw_record_index(
                    conn,
                    temp_table_name=temp_table_name,
                    table_name=table_name,
                    load_run_id=load_run_id,
                    loaded_at_utc=loaded_at_utc,
                )

        conn.commit()
        mark_ingestion_finished(
            conn,
            table_name=table_name,
            load_run_id=load_run_id,
            status="success",
            row_count=row_count,
            inserted_count=inserted_count,
            completed_at_utc=now_utc(),
        )
    except Exception:
        conn.rollback()
        mark_ingestion_finished(
            conn,
            table_name=table_name,
            load_run_id=load_run_id,
            status="failed",
            row_count=row_count,
            inserted_count=inserted_count,
            completed_at_utc=now_utc(),
        )
        raise
    finally:
        temp_csv_path.unlink(missing_ok=True)

    return {
        "rows": row_count,
        "inserted": inserted_count,
        "skipped": max(0, row_count - inserted_count),
    }


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
            truncate_tables(conn, ALL_TABLES + STATE_TABLES)

        for table_name, csv_path in loads:
            print(f"Loading {display_path(csv_path)} -> {table_name}")
            result = copy_csv(
                conn,
                table_name,
                csv_path,
                load_run_id=args.run_id,
                dataset=args.dataset,
            )
            print(
                f"  rows={result['rows']} "
                f"inserted={result['inserted']} "
                f"skipped={result['skipped']}"
            )

    print("PostgreSQL load complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
