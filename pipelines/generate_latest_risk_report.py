from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_BACKFILL_DIR = PROJECT_ROOT / "data" / "processed" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in PROCESSED_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed backfill run directory under {PROCESSED_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Latest Recall Risk Score Report",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Latest week: `{summary['latest_week']}`",
        f"- Input CSV: `{summary['input_csv']}`",
        "",
        "## What this score means",
        "",
        "`baseline_risk_score`는 리콜 확률 그 자체가 아니다. 현재 MVP에서는 최근 complaint count가 과거 8주 평균 대비 얼마나 튀었는지를 나타내는 조기 신호 점수다.",
        "",
        "해석:",
        "",
        "```text",
        "높은 점수 = 최근 해당 차량/부품 조합의 complaint spike가 있었다",
        "낮은 점수 = 최근 spike 신호가 약하다",
        "```",
        "",
        "## Top Risk Scores",
        "",
        "| Rank | Make | Model | Year | Component | Week | Complaints | Severe | Spike Z | Score |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]

    for row in summary["top_rows"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_primary']} | {row['week_start']} "
            f"| {row['complaint_count']} | {row['severe_complaint_count']} "
            f"| {row['complaint_spike_z']} | {row['baseline_risk_score']} |"
        )

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- 이 리포트는 MVP baseline 신호다.",
            "- complaint spike만 사용하므로 실제 recall decision을 충분히 설명하지 못한다.",
            "- 최신 주에는 complaint count가 1건이어도 과거 평균이 낮으면 spike score가 높게 나올 수 있다.",
            "- F-150처럼 complaints endpoint coverage가 약한 모델은 risk score가 과소평가될 수 있다.",
            "- 리콜 확률 모델로 쓰려면 component mapping, investigation data, calibration 개선이 필요하다.",
            "",
            "## Next",
            "",
            "MVP 마지막 단계에서는 README와 전체 재현 절차를 정리한다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate latest risk score report.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--top-k", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    input_csv = processed_run_dir / "latest_risk_scores.csv"
    rows = read_csv(input_csv)
    rows = rows[: args.top_k]

    latest_week = rows[0]["week_start"] if rows else ""
    summary = {
        "source_run_id": run_id,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "input_csv": display_path(input_csv),
        "latest_week": latest_week,
        "top_k": args.top_k,
        "top_rows": rows,
    }

    summary_path = processed_run_dir / "latest_risk_report_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "latest_risk_score_report.md"
    write_markdown_report(summary, report_path)

    docs_result_path = DOCS_DIR / "LATEST_RISK_SCORE_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Latest week: {latest_week}")
    print(f"Rows:        {len(rows)}")
    print(f"Wrote:       {display_path(report_path)}")
    print(f"Wrote:       {display_path(docs_result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

