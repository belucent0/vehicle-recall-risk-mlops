from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"

NHTSA_BASE_URL = "https://api.nhtsa.gov"

DEFAULT_VEHICLES = [
    {"make": "HYUNDAI", "model": "SANTA FE", "model_year": 2022},
    {"make": "KIA", "model": "TELLURIDE", "model_year": 2022},
    {"make": "TESLA", "model": "MODEL 3", "model_year": 2022},
    {"make": "FORD", "model": "F-150", "model_year": 2022},
    {"make": "TOYOTA", "model": "RAV4", "model_year": 2022},
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def fetch_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{NHTSA_BASE_URL}{endpoint}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "nhtsa-recall-risk-mlops/0.1"})

    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset)
            status_code = response.status
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        # Some NHTSA endpoints occasionally return HTTP 400 with a JSON body that
        # still has a normal-looking empty result payload. Preserve the response
        # so the smoke test can reveal endpoint/model quirks instead of failing
        # the whole run.
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as json_exc:
            raise RuntimeError(f"HTTP {exc.code} while requesting {url}: {body[:500]}") from exc
        payload["_request"] = {
            "url": url,
            "endpoint": endpoint,
            "params": params,
            "fetched_at_utc": datetime.now(UTC).isoformat(),
        }
        payload["_response"] = {"http_status": exc.code, "treated_as_payload": True}
        return payload
    except URLError as exc:
        raise RuntimeError(f"Network error while requesting {url}: {exc}") from exc

    payload = json.loads(raw)
    payload["_request"] = {
        "url": url,
        "endpoint": endpoint,
        "params": params,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
    }
    payload["_response"] = {"http_status": status_code, "treated_as_payload": False}
    return payload


def get_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") or payload.get("Results") or []
    if not isinstance(results, list):
        raise ValueError(f"Unexpected response shape. results type={type(results)}")
    return results


def collect_vehicle(vehicle: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    make = vehicle["make"]
    model = vehicle["model"]
    model_year = vehicle["model_year"]

    params = {"make": make, "model": model, "modelYear": model_year}
    vehicle_slug = f"{slugify(make)}_{slugify(model)}_{model_year}"

    complaints = fetch_json("/complaints/complaintsByVehicle", params)
    recalls = fetch_json("/recalls/recallsByVehicle", params)

    complaints_path = output_dir / f"{vehicle_slug}_complaints.json"
    recalls_path = output_dir / f"{vehicle_slug}_recalls.json"

    complaints_path.write_text(json.dumps(complaints, indent=2, ensure_ascii=False), encoding="utf-8")
    recalls_path.write_text(json.dumps(recalls, indent=2, ensure_ascii=False), encoding="utf-8")

    complaint_results = get_results(complaints)
    recall_results = get_results(recalls)

    return {
        "vehicle": vehicle,
        "complaints_count": len(complaint_results),
        "recalls_count": len(recall_results),
        "complaints_http_status": complaints.get("_response", {}).get("http_status"),
        "recalls_http_status": recalls.get("_response", {}).get("http_status"),
        "complaints_keys": sorted(complaint_results[0].keys()) if complaint_results else [],
        "recalls_keys": sorted(recall_results[0].keys()) if recall_results else [],
        "complaints_path": str(complaints_path.relative_to(PROJECT_ROOT)),
        "recalls_path": str(recalls_path.relative_to(PROJECT_ROOT)),
    }


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# NHTSA Smoke Test Report",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Fetched at UTC: `{summary['fetched_at_utc']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Counts",
        "",
        "| Make | Model | Year | Complaints | Recalls | Complaints HTTP | Recalls HTTP |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for item in summary["vehicles"]:
        vehicle = item["vehicle"]
        lines.append(
            f"| {vehicle['make']} | {vehicle['model']} | {vehicle['model_year']} "
            f"| {item['complaints_count']} | {item['recalls_count']} "
            f"| {item['complaints_http_status']} | {item['recalls_http_status']} |"
        )

    lines.extend(["", "## Observed Keys", ""])

    for item in summary["vehicles"]:
        vehicle = item["vehicle"]
        title = f"{vehicle['make']} {vehicle['model']} {vehicle['model_year']}"
        lines.extend(
            [
                f"### {title}",
                "",
                f"- Complaints keys: `{', '.join(item['complaints_keys'])}`",
                f"- Recalls keys: `{', '.join(item['recalls_keys'])}`",
                "",
            ]
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect NHTSA sample complaints and recalls.")
    parser.add_argument(
        "--run-id",
        default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        help="Run ID used for the output directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = RAW_DIR / "smoke_test" / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "run_id": args.run_id,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "vehicles": [],
    }

    for vehicle in DEFAULT_VEHICLES:
        print(
            f"Fetching {vehicle['make']} {vehicle['model']} {vehicle['model_year']}...",
            flush=True,
        )
        item = collect_vehicle(vehicle, output_dir)
        summary["vehicles"].append(item)
        print(
            f"  complaints={item['complaints_count']} recalls={item['recalls_count']}",
            flush=True,
        )

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    latest_report_path = REPORTS_DIR / "smoke_test_latest.md"
    write_markdown_report(summary, latest_report_path)

    print("")
    print(f"Wrote summary: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote report:  {latest_report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
