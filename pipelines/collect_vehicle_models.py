from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

VPIC_BASE_URL = "https://vpic.nhtsa.dot.gov/api"

DEFAULT_MAKES = ["HYUNDAI", "KIA", "TOYOTA", "FORD", "TESLA"]
DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR = 2026

VEHICLE_MODEL_COLUMNS = [
    "make_query",
    "model_year",
    "make_id",
    "make_name",
    "model_id",
    "model_name",
    "model_name_normalized",
    "source",
    "fetched_at_utc",
]


def normalize_model_name(value: str) -> str:
    text = (value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def fetch_vpic_models(make: str, model_year: int) -> dict[str, Any]:
    make_path = quote(make.strip())
    url = f"{VPIC_BASE_URL}/vehicles/GetModelsForMakeYear/make/{make_path}/modelyear/{model_year}"
    full_url = f"{url}?format=json"
    request = Request(full_url, headers={"User-Agent": "nhtsa-recall-risk-mlops/0.1"})

    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset)
            status_code = response.status
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} while requesting {full_url}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while requesting {full_url}: {exc}") from exc

    payload = json.loads(raw)
    payload["_request"] = {
        "url": full_url,
        "make": make,
        "model_year": model_year,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
    }
    payload["_response"] = {"http_status": status_code}
    return payload


def rows_from_payload(make_query: str, model_year: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("Results") or payload.get("results") or []
    if not isinstance(results, list):
        raise ValueError(f"Unexpected VPIC response shape: {type(results)}")

    fetched_at = payload["_request"]["fetched_at_utc"]
    rows = []
    for item in results:
        if not isinstance(item, dict):
            continue
        model_name = str(item.get("Model_Name") or "").strip().upper()
        rows.append(
            {
                "make_query": make_query.upper(),
                "model_year": model_year,
                "make_id": item.get("Make_ID") or "",
                "make_name": str(item.get("Make_Name") or "").strip().upper(),
                "model_id": item.get("Model_ID") or "",
                "model_name": model_name,
                "model_name_normalized": normalize_model_name(model_name),
                "source": "vpic_get_models_for_make_year",
                "fetched_at_utc": fetched_at,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VEHICLE_MODEL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_make = Counter(row["make_query"] for row in rows)
    by_year = Counter(str(row["model_year"]) for row in rows)
    make_year_counts: dict[str, dict[str, int]] = defaultdict(dict)
    unique_models_by_make: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        make = row["make_query"]
        year = str(row["model_year"])
        make_year_counts[make][year] = make_year_counts[make].get(year, 0) + 1
        unique_models_by_make[make].add(row["model_name_normalized"])

    f_series_rows = [
        row
        for row in rows
        if row["make_query"] == "FORD"
        and (
            "F 150" in row["model_name_normalized"]
            or "F150" in row["model_name_normalized"]
            or "F-150" in row["model_name"]
        )
    ]

    return {
        "row_count": len(rows),
        "make_count": len(by_make),
        "year_count": len(by_year),
        "by_make": dict(sorted(by_make.items())),
        "by_year": dict(sorted(by_year.items())),
        "unique_model_count_by_make": {
            make: len(models) for make, models in sorted(unique_models_by_make.items())
        },
        "ford_f150_like_rows": f_series_rows[:50],
    }


def write_markdown_report(summary: dict[str, Any], output_csv: Path, report_path: Path) -> None:
    lines = [
        "# VPIC Vehicle Model List Results",
        "",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Output CSV: `{output_csv.relative_to(PROJECT_ROOT)}`",
        f"- Total rows: `{summary['row_count']}`",
        "",
        "## Counts by Make",
        "",
        "| Make | Rows | Unique normalized models |",
        "|---|---:|---:|",
    ]

    for make, count in summary["by_make"].items():
        unique_count = summary["unique_model_count_by_make"].get(make, 0)
        lines.append(f"| {make} | {count} | {unique_count} |")

    lines.extend(["", "## Counts by Year", "", "| Year | Rows |", "|---:|---:|"])
    for year, count in summary["by_year"].items():
        lines.append(f"| {year} | {count} |")

    lines.extend(
        [
            "",
            "## FORD F-150-like Model Names",
            "",
            "| Year | Make Name | Model Name | Normalized | Model ID |",
            "|---:|---|---|---|---:|",
        ]
    )

    for row in summary["ford_f150_like_rows"]:
        lines.append(
            f"| {row['model_year']} | {row['make_name']} | {row['model_name']} "
            f"| {row['model_name_normalized']} | {row['model_id']} |"
        )

    if not summary["ford_f150_like_rows"]:
        lines.append("| - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- 이 결과는 backfill collector가 순회할 제조사/연식/모델 후보 목록이다.",
            "- 같은 모델도 연식별로 반복되므로 row 수는 unique model 수보다 크다.",
            "- 다음 단계에서는 이 목록을 NHTSA complaints/recalls endpoint에 넣어 실제 수집 성공률을 확인한다.",
            "- FORD F-150처럼 API endpoint별 모델명 표기가 달라질 수 있으므로 alias 정규화가 필요하다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect VPIC vehicle model list.")
    parser.add_argument("--makes", nargs="+", default=DEFAULT_MAKES)
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[dict[str, Any]] = []

    for make in args.makes:
        for model_year in range(args.start_year, args.end_year + 1):
            print(f"Fetching VPIC models: {make.upper()} {model_year}...", flush=True)
            payload = fetch_vpic_models(make, model_year)
            year_rows = rows_from_payload(make, model_year, payload)
            rows.extend(year_rows)
            print(f"  models={len(year_rows)}", flush=True)

    rows.sort(key=lambda row: (row["make_query"], row["model_year"], row["model_name_normalized"]))

    output_csv = INTERIM_DIR / "vehicle_models.csv"
    write_csv(output_csv, rows)

    summary = summarize(rows)
    summary["built_at_utc"] = datetime.now(UTC).isoformat()
    summary["makes"] = [make.upper() for make in args.makes]
    summary["start_year"] = args.start_year
    summary["end_year"] = args.end_year
    summary["output_csv"] = str(output_csv.relative_to(PROJECT_ROOT))

    summary_path = INTERIM_DIR / "vehicle_models_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "vehicle_models_latest.md"
    write_markdown_report(summary, output_csv, report_path)

    docs_result_path = DOCS_DIR / "VEHICLE_MODELS_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print("")
    print(f"Rows:  {summary['row_count']}")
    print(f"Wrote: {output_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {report_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {docs_result_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

