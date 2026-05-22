from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recall_risk.ingestion.normalize import (
    COMPLAINT_COLUMNS,
    RECALL_COLUMNS,
    normalize_complaint,
    normalize_recall,
    read_nhtsa_results,
    summarize_rows,
    write_csv,
)


RAW_SMOKE_DIR = PROJECT_ROOT / "data" / "raw" / "smoke_test"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "smoke_test"
REPORTS_DIR = PROJECT_ROOT / "reports"


def latest_run_dir() -> Path:
    candidates = [path for path in RAW_SMOKE_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No smoke test run directory under {RAW_SMOKE_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize NHTSA smoke test raw JSON.")
    parser.add_argument("--run-id", help="Smoke test run id. Defaults to latest raw run.")
    return parser.parse_args()


def write_markdown_report(summary: dict[str, Any], path: Path) -> None:
    complaint = summary["complaints"]
    recall = summary["recalls"]

    lines = [
        "# NHTSA Normalized Sample Report",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Normalized at UTC: `{summary['normalized_at_utc']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Row Counts",
        "",
        "| Table | Rows | Min Date | Max Date |",
        "|---|---:|---:|---:|",
        (
            f"| complaints | {complaint['row_count']} | "
            f"{complaint['min_date']} | {complaint['max_date']} |"
        ),
        f"| recalls | {recall['row_count']} | {recall['min_date']} | {recall['max_date']} |",
        "",
        "## Top Complaint Components",
        "",
        "| Component | Count |",
        "|---|---:|",
    ]

    lines.extend([f"| {name} | {count} |" for name, count in complaint["top_components"]])

    lines.extend(["", "## Top Recall Components", "", "| Component | Count |", "|---|---:|"])
    lines.extend([f"| {name} | {count} |" for name, count in recall["top_components"]])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    raw_run_dir = RAW_SMOKE_DIR / args.run_id if args.run_id else latest_run_dir()
    if not raw_run_dir.exists():
        raise FileNotFoundError(raw_run_dir)

    run_id = raw_run_dir.name
    output_dir = INTERIM_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    complaint_rows = []
    recall_rows = []

    for path in sorted(raw_run_dir.glob("*_complaints.json")):
        complaint_rows.extend(normalize_complaint(record) for record in read_nhtsa_results(path))

    for path in sorted(raw_run_dir.glob("*_recalls.json")):
        recall_rows.extend(normalize_recall(record) for record in read_nhtsa_results(path))

    complaints_path = output_dir / "complaints.csv"
    recalls_path = output_dir / "recalls.csv"

    write_csv(complaints_path, complaint_rows, COMPLAINT_COLUMNS)
    write_csv(recalls_path, recall_rows, RECALL_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "normalized_at_utc": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "complaints_csv": str(complaints_path.relative_to(PROJECT_ROOT)),
        "recalls_csv": str(recalls_path.relative_to(PROJECT_ROOT)),
        "complaints": summarize_rows(complaint_rows, "date_complaint_filed", "component_primary"),
        "recalls": summarize_rows(recall_rows, "report_received_date", "component_primary"),
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    latest_report_path = REPORTS_DIR / "normalized_sample_latest.md"
    write_markdown_report(summary, latest_report_path)

    print(f"Normalized complaints rows: {summary['complaints']['row_count']}")
    print(f"Normalized recalls rows:    {summary['recalls']['row_count']}")
    print(f"Wrote: {complaints_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {recalls_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {latest_report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
