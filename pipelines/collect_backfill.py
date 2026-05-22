from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MODELS_PATH = PROJECT_ROOT / "data" / "interim" / "vehicle_models.csv"
RAW_BACKFILL_DIR = PROJECT_ROOT / "data" / "raw" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

NHTSA_BASE_URL = "https://api.nhtsa.gov"

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


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def read_vehicle_models(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    vehicles = []
    seen = set()
    for row in rows:
        make = (row.get("make_query") or row.get("make_name") or "").strip().upper()
        model = (row.get("model_name") or "").strip().upper()
        model_year = str(row.get("model_year") or "").strip()
        key = (make, model, model_year)
        if not all(key) or key in seen:
            continue
        seen.add(key)
        vehicles.append({"make": make, "model": model, "model_year": model_year})

    vehicles.sort(key=lambda item: (item["make"], item["model_year"], item["model"]))
    return vehicles


def filter_vehicles(
    vehicles: list[dict[str, str]],
    makes: list[str] | None,
    start_year: int | None,
    end_year: int | None,
    limit: int | None,
) -> list[dict[str, str]]:
    if makes:
        make_set = {make.strip().upper() for make in makes}
        vehicles = [vehicle for vehicle in vehicles if vehicle["make"] in make_set]
    if start_year is not None:
        vehicles = [vehicle for vehicle in vehicles if int(vehicle["model_year"]) >= start_year]
    if end_year is not None:
        vehicles = [vehicle for vehicle in vehicles if int(vehicle["model_year"]) <= end_year]
    if limit is not None:
        vehicles = vehicles[:limit]
    return vehicles


def fetch_nhtsa(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{NHTSA_BASE_URL}{endpoint}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "nhtsa-recall-risk-mlops/0.1"})

    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset)
            status_code = response.status
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status_code = exc.code
    except URLError as exc:
        return {
            "count": 0,
            "message": f"Network error: {exc}",
            "results": [],
            "_request": {
                "url": url,
                "endpoint": endpoint,
                "params": params,
                "fetched_at_utc": datetime.now(UTC).isoformat(),
            },
            "_response": {"http_status": "NETWORK_ERROR"},
        }

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {"count": 0, "message": body[:500], "results": []}

    payload["_request"] = {
        "url": url,
        "endpoint": endpoint,
        "params": params,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
    }
    payload["_response"] = {"http_status": status_code}
    return payload


def get_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") or payload.get("Results") or []
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def endpoint_specs() -> list[tuple[str, str]]:
    return [
        ("complaints", "/complaints/complaintsByVehicle"),
        ("recalls", "/recalls/recallsByVehicle"),
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def collect_vehicle(
    run_id: str,
    output_dir: Path,
    vehicle_index: int,
    vehicle: dict[str, str],
    sleep_seconds: float = 0.0,
) -> list[dict[str, Any]]:
    make = vehicle["make"]
    model = vehicle["model"]
    model_year = vehicle["model_year"]

    rows = []
    for endpoint_name, endpoint_path in endpoint_specs():
        params = {"make": make, "model": model, "modelYear": model_year}
        payload = fetch_nhtsa(endpoint_path, params)
        results = get_results(payload)

        filename = (
            f"{vehicle_index:05d}_{slugify(make)}_{slugify(model)}_"
            f"{model_year}_{endpoint_name}.json"
        )
        raw_path = output_dir / filename
        write_json(raw_path, payload)

        rows.append(
            {
                "run_id": run_id,
                "vehicle_index": vehicle_index,
                "make": make,
                "model": model,
                "model_year": model_year,
                "endpoint": endpoint_name,
                "http_status": payload.get("_response", {}).get("http_status"),
                "count": len(results),
                "message": payload.get("message") or payload.get("Message") or "",
                "raw_path": str(raw_path.relative_to(PROJECT_ROOT)),
                "url": payload.get("_request", {}).get("url", ""),
                "fetched_at_utc": payload.get("_request", {}).get("fetched_at_utc", ""),
            }
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return rows


def summarize(manifest_rows: list[dict[str, Any]], selected_vehicles: list[dict[str, str]]) -> dict[str, Any]:
    endpoint_counts = Counter(row["endpoint"] for row in manifest_rows)
    endpoint_rows: dict[str, list[dict[str, Any]]] = {
        endpoint: [row for row in manifest_rows if row["endpoint"] == endpoint]
        for endpoint in endpoint_counts
    }

    summary_by_endpoint = {}
    for endpoint, rows in endpoint_rows.items():
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

    issue_rows = [
        row
        for row in manifest_rows
        if row["endpoint"] == "complaints"
        and int(row["count"]) == 0
    ]
    issue_keys = {
        (row["make"], row["model"], row["model_year"])
        for row in issue_rows
    }

    return {
        "vehicle_count": len(selected_vehicles),
        "request_count": len(manifest_rows),
        "summary_by_endpoint": summary_by_endpoint,
        "complaints_empty_vehicle_count": len(issue_keys),
        "sample_complaints_empty_vehicles": [
            {"make": make, "model": model, "model_year": model_year}
            for make, model, model_year in sorted(issue_keys)[:20]
        ],
    }


def write_markdown_report(summary: dict[str, Any], manifest_path: Path, report_path: Path) -> None:
    lines = [
        "# Backfill Collection Results",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Vehicle count: `{summary['vehicle_count']}`",
        f"- Request count: `{summary['request_count']}`",
        f"- Manifest: `{manifest_path.relative_to(PROJECT_ROOT)}`",
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
            "- 이 작업은 전체 backfill 전에 collector가 여러 차량을 순회하며 raw JSON과 manifest를 남기는지 확인하는 단계다.",
            "- HTTP 400 empty result도 실패로 중단하지 않고 manifest에 기록한다.",
            "- 다음 단계는 이 backfill raw output을 정규화하는 파이프라인을 일반화하는 것이다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect NHTSA complaints/recalls for vehicle model list.")
    parser.add_argument("--vehicle-models", default=str(VEHICLE_MODELS_PATH))
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--makes", nargs="+", help="Optional make filter.")
    parser.add_argument("--start-year", type=int, help="Optional model year start.")
    parser.add_argument("--end-year", type=int, help="Optional model year end.")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max vehicles to collect. Use 0 for no limit. Default is 50 for safe MVP iteration.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vehicle_models_path = Path(args.vehicle_models)
    vehicles = read_vehicle_models(vehicle_models_path)
    limit = None if args.limit == 0 else args.limit
    selected = filter_vehicles(vehicles, args.makes, args.start_year, args.end_year, limit)

    run_id = args.run_id
    output_dir = RAW_BACKFILL_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Selected vehicles: {len(selected)}", flush=True)
    manifest_rows: list[dict[str, Any]] = []

    for idx, vehicle in enumerate(selected, start=1):
        print(
            f"[{idx}/{len(selected)}] {vehicle['make']} {vehicle['model']} {vehicle['model_year']}",
            flush=True,
        )
        rows = collect_vehicle(run_id, output_dir, idx, vehicle, args.sleep_seconds)
        manifest_rows.extend(rows)
        counts = {row["endpoint"]: row["count"] for row in rows}
        statuses = {row["endpoint"]: row["http_status"] for row in rows}
        print(
            f"  complaints={counts.get('complaints')}({statuses.get('complaints')}) "
            f"recalls={counts.get('recalls')}({statuses.get('recalls')})",
            flush=True,
        )

    manifest_path = output_dir / "manifest.csv"
    write_manifest(manifest_path, manifest_rows)

    summary = summarize(manifest_rows, selected)
    summary["run_id"] = run_id
    summary["built_at_utc"] = datetime.now(UTC).isoformat()
    summary["vehicle_models_csv"] = display_path(vehicle_models_path)
    summary["raw_output_dir"] = display_path(output_dir)
    summary["manifest_csv"] = display_path(manifest_path)
    summary["filters"] = {
        "makes": args.makes,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "limit": args.limit,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "backfill_collection_latest.md"
    write_markdown_report(summary, manifest_path, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_COLLECTION_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print("")
    print(f"Requests: {summary['request_count']}")
    print(f"Wrote:    {manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:    {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:    {report_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:    {docs_result_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
