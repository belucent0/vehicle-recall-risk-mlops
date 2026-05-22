from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recall_risk.ingestion.normalize import (  # noqa: E402
    COMPLAINT_COLUMNS,
    RECALL_COLUMNS,
    normalize_complaint,
    normalize_recall,
    read_nhtsa_results,
    summarize_rows,
    write_csv,
)


RAW_BACKFILL_DIR = PROJECT_ROOT / "data" / "raw" / "backfill"
INTERIM_BACKFILL_DIR = PROJECT_ROOT / "data" / "interim" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in RAW_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No backfill raw directories under {RAW_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def top_entities(rows: list[dict[str, Any]], limit: int = 15) -> list[tuple[str, int]]:
    counts = Counter(
        f"{row.get('make')} {row.get('model')} {row.get('model_year')}"
        for row in rows
        if row.get("make") and row.get("model") and row.get("model_year")
    )
    return counts.most_common(limit)


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    complaints = summary["complaints"]
    recalls = summary["recalls"]

    lines = [
        "# Backfill Normalization Results",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Normalized at UTC: `{summary['normalized_at_utc']}`",
        f"- Source raw dir: `{summary['source_raw_dir']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Row Counts",
        "",
        "| Table | Rows | Min Date | Max Date |",
        "|---|---:|---:|---:|",
        (
            f"| complaints | {complaints['row_count']} | "
            f"{complaints['min_date']} | {complaints['max_date']} |"
        ),
        f"| recalls | {recalls['row_count']} | {recalls['min_date']} | {recalls['max_date']} |",
        "",
        "## Top Complaint Components",
        "",
        "| Component | Count |",
        "|---|---:|",
    ]

    for name, count in complaints["top_components"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(["", "## Top Recall Components", "", "| Component | Count |", "|---|---:|"])
    for name, count in recalls["top_components"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(["", "## Top Complaint Vehicle-Year Entities", "", "| Entity | Rows |", "|---|---:|"])
    for name, count in summary["top_complaint_entities"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(["", "## Top Recall Vehicle-Year Entities", "", "| Entity | Rows |", "|---|---:|"])
    for name, count in summary["top_recall_entities"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- MVP backfill raw JSON을 분석 가능한 CSV로 변환했다.",
            "- 다음 단계에서는 이 CSV를 사용해 weekly features와 90일 recall labels를 다시 생성한다.",
            "- 이 단계부터는 smoke test가 아니라 MVP 데이터셋을 다루는 단계다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize NHTSA backfill raw JSON.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest raw backfill run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_run_dir = RAW_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not raw_run_dir.exists():
        raise FileNotFoundError(raw_run_dir)

    run_id = raw_run_dir.name
    output_dir = INTERIM_BACKFILL_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    complaint_rows = []
    recall_rows = []

    complaint_files = sorted(raw_run_dir.glob("*_complaints.json"))
    recall_files = sorted(raw_run_dir.glob("*_recalls.json"))

    for idx, path in enumerate(complaint_files, start=1):
        if idx % 100 == 0:
            print(f"Normalizing complaints file {idx}/{len(complaint_files)}", flush=True)
        complaint_rows.extend(normalize_complaint(record) for record in read_nhtsa_results(path))

    for idx, path in enumerate(recall_files, start=1):
        if idx % 100 == 0:
            print(f"Normalizing recalls file {idx}/{len(recall_files)}", flush=True)
        recall_rows.extend(normalize_recall(record) for record in read_nhtsa_results(path))

    complaints_path = output_dir / "complaints.csv"
    recalls_path = output_dir / "recalls.csv"

    write_csv(complaints_path, complaint_rows, COMPLAINT_COLUMNS)
    write_csv(recalls_path, recall_rows, RECALL_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "normalized_at_utc": datetime.now(UTC).isoformat(),
        "source_raw_dir": display_path(raw_run_dir),
        "output_dir": display_path(output_dir),
        "complaints_csv": display_path(complaints_path),
        "recalls_csv": display_path(recalls_path),
        "complaints_file_count": len(complaint_files),
        "recalls_file_count": len(recall_files),
        "complaints": summarize_rows(complaint_rows, "date_complaint_filed", "component_primary"),
        "recalls": summarize_rows(recall_rows, "report_received_date", "component_primary"),
        "top_complaint_entities": top_entities(complaint_rows),
        "top_recall_entities": top_entities(recall_rows),
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "backfill_normalization_latest.md"
    write_markdown_report(summary, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_NORMALIZATION_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Normalized complaints rows: {summary['complaints']['row_count']}")
    print(f"Normalized recalls rows:    {summary['recalls']['row_count']}")
    print(f"Wrote: {display_path(complaints_path)}")
    print(f"Wrote: {display_path(recalls_path)}")
    print(f"Wrote: {display_path(report_path)}")
    print(f"Wrote: {display_path(docs_result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

