from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_BACKFILL_DIR = PROJECT_ROOT / "data" / "raw" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

MANIFEST_COLUMNS = [
    "run_id",
    "vehicle_index",
    "make",
    "model",
    "model_year",
    "endpoint",
    "http_status",
    "count",
    "message",
    "raw_path",
    "url",
    "fetched_at_utc",
]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in RAW_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No backfill directories under {RAW_BACKFILL_DIR}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def get_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") or payload.get("Results") or []
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def parse_vehicle_index(path: Path) -> int:
    match = re.match(r"(?P<idx>\d+)_", path.name)
    return int(match.group("idx")) if match else 0


def endpoint_from_payload(path: Path, payload: dict[str, Any]) -> str:
    endpoint = str(payload.get("_request", {}).get("endpoint", ""))
    if "complaints" in endpoint.lower() or path.name.endswith("_complaints.json"):
        return "complaints"
    if "recalls" in endpoint.lower() or path.name.endswith("_recalls.json"):
        return "recalls"
    return "unknown"


def recover_manifest(run_dir: Path) -> list[dict[str, Any]]:
    run_id = run_dir.name
    rows = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name in {"summary.json"}:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = payload.get("_request", {})
        params = request.get("params", {})
        response = payload.get("_response", {})
        endpoint = endpoint_from_payload(path, payload)
        results = get_results(payload)
        rows.append(
            {
                "run_id": run_id,
                "vehicle_index": parse_vehicle_index(path),
                "make": str(params.get("make") or "").upper(),
                "model": str(params.get("model") or "").upper(),
                "model_year": str(params.get("modelYear") or ""),
                "endpoint": endpoint,
                "http_status": response.get("http_status", ""),
                "count": len(results),
                "message": payload.get("message") or payload.get("Message") or "",
                "raw_path": display_path(path),
                "url": request.get("url", ""),
                "fetched_at_utc": request.get("fetched_at_utc", ""),
            }
        )
    return rows


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(manifest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    vehicle_keys = {
        (row["make"], row["model"], row["model_year"])
        for row in manifest_rows
        if row["make"] and row["model"] and row["model_year"]
    }

    endpoints = sorted({row["endpoint"] for row in manifest_rows})
    summary_by_endpoint = {}
    for endpoint in endpoints:
        rows = [row for row in manifest_rows if row["endpoint"] == endpoint]
        statuses = Counter(str(row["http_status"]) for row in rows)
        nonempty = [row for row in rows if int(row["count"]) > 0]
        empty = [row for row in rows if int(row["count"]) == 0]
        summary_by_endpoint[endpoint] = {
            "requests": len(rows),
            "nonempty": len(nonempty),
            "empty": len(empty),
            "status_counts": dict(sorted(statuses.items())),
            "total_records": sum(int(row["count"]) for row in rows),
        }

    complaints_empty_keys = {
        (row["make"], row["model"], row["model_year"])
        for row in manifest_rows
        if row["endpoint"] == "complaints" and int(row["count"]) == 0
    }

    return {
        "vehicle_count": len(vehicle_keys),
        "request_count": len(manifest_rows),
        "summary_by_endpoint": summary_by_endpoint,
        "complaints_empty_vehicle_count": len(complaints_empty_keys),
        "sample_complaints_empty_vehicles": [
            {"make": make, "model": model, "model_year": model_year}
            for make, model, model_year in sorted(complaints_empty_keys)[:30]
        ],
    }


def write_markdown_report(summary: dict[str, Any], manifest_path: Path, report_path: Path) -> None:
    lines = [
        "# MVP Backfill Collection Results",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Vehicle count: `{summary['vehicle_count']}`",
        f"- Request count: `{summary['request_count']}`",
        f"- Manifest: `{display_path(manifest_path)}`",
        f"- Raw output dir: `{summary['raw_output_dir']}`",
        "",
        "## Endpoint Summary",
        "",
        "| Endpoint | Requests | Non-empty | Empty | Total records | Status counts |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for endpoint, item in sorted(summary["summary_by_endpoint"].items()):
        lines.append(
            f"| {endpoint} | {item['requests']} | {item['nonempty']} | {item['empty']} "
            f"| {item['total_records']} | `{item['status_counts']}` |"
        )

    lines.extend(
        [
            "",
            "## Sample vehicles with empty complaints",
            "",
            "| Make | Model | Year |",
            "|---|---|---:|",
        ]
    )
    for item in summary["sample_complaints_empty_vehicles"]:
        lines.append(f"| {item['make']} | {item['model']} | {item['model_year']} |")
    if not summary["sample_complaints_empty_vehicles"]:
        lines.append("| - | - | - |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `vehicle_models_mvp.csv` 기반 raw JSON 수집은 완료되었다.",
            "- 원래 collector가 summary 작성 단계에서 상대경로 처리 오류로 종료되어, raw JSON에서 manifest와 summary를 복구했다.",
            "- 수집 파일 자체는 모두 저장되어 있었으므로 재수집하지 않았다.",
            "- 다음 단계는 이 backfill raw output을 complaints/recalls CSV로 정규화하는 것이다.",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover manifest/summary from saved backfill raw JSON.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest backfill directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = RAW_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not run_dir.exists():
        raise FileNotFoundError(run_dir)

    manifest_rows = recover_manifest(run_dir)
    manifest_path = run_dir / "manifest.csv"
    write_manifest(manifest_path, manifest_rows)

    summary = summarize(manifest_rows)
    summary["run_id"] = run_dir.name
    summary["built_at_utc"] = datetime.now(UTC).isoformat()
    summary["raw_output_dir"] = display_path(run_dir)
    summary["manifest_csv"] = display_path(manifest_path)

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "backfill_collection_latest.md"
    write_markdown_report(summary, manifest_path, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_COLLECTION_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Recovered run: {run_dir.name}")
    print(f"Vehicles:      {summary['vehicle_count']}")
    print(f"Requests:      {summary['request_count']}")
    print(f"Wrote:         {display_path(manifest_path)}")
    print(f"Wrote:         {display_path(summary_path)}")
    print(f"Wrote:         {display_path(report_path)}")
    print(f"Wrote:         {display_path(docs_result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

