from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "model_aliases.yaml"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

NHTSA_BASE_URL = "https://api.nhtsa.gov"

OUTPUT_COLUMNS = [
    "make",
    "canonical_model",
    "model_year",
    "candidate_model",
    "endpoint",
    "http_status",
    "count",
    "message",
    "observed_models",
    "observed_makes",
    "url",
    "fetched_at_utc",
]


def load_config(path: Path) -> dict[str, Any]:
    # The file is JSON-formatted YAML, so stdlib json is enough for now.
    return json.loads(path.read_text(encoding="utf-8"))


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
        raise RuntimeError(f"Network error while requesting {url}: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {"count": "", "message": body[:500], "results": []}

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


def observed_from_complaints(results: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    models: Counter[str] = Counter()
    makes: Counter[str] = Counter()

    for row in results:
        products = row.get("products") or []
        if not isinstance(products, list):
            continue
        for product in products:
            if not isinstance(product, dict):
                continue
            if str(product.get("type", "")).lower() != "vehicle":
                continue
            model = str(product.get("productModel") or "").strip().upper()
            make = str(product.get("productMake") or "").strip().upper()
            if model:
                models[model] += 1
            if make:
                makes[make] += 1

    return sorted(models), sorted(makes)


def observed_from_recalls(results: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    models = sorted({str(row.get("Model") or "").strip().upper() for row in results if row.get("Model")})
    makes = sorted({str(row.get("Make") or "").strip().upper() for row in results if row.get("Make")})
    return models, makes


def check_candidate(make: str, canonical_model: str, model_year: int, candidate: str) -> list[dict[str, Any]]:
    endpoint_specs = [
        ("complaints", "/complaints/complaintsByVehicle"),
        ("recalls", "/recalls/recallsByVehicle"),
    ]

    rows: list[dict[str, Any]] = []
    for endpoint_name, endpoint_path in endpoint_specs:
        params = {"make": make, "model": candidate, "modelYear": model_year}
        payload = fetch_nhtsa(endpoint_path, params)
        results = get_results(payload)
        if endpoint_name == "complaints":
            observed_models, observed_makes = observed_from_complaints(results)
        else:
            observed_models, observed_makes = observed_from_recalls(results)

        rows.append(
            {
                "make": make,
                "canonical_model": canonical_model,
                "model_year": model_year,
                "candidate_model": candidate,
                "endpoint": endpoint_name,
                "http_status": payload.get("_response", {}).get("http_status"),
                "count": len(results),
                "message": payload.get("message") or payload.get("Message") or "",
                "observed_models": "|".join(observed_models),
                "observed_makes": "|".join(observed_makes),
                "url": payload.get("_request", {}).get("url", ""),
                "fetched_at_utc": payload.get("_request", {}).get("fetched_at_utc", ""),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["make"], row["canonical_model"], int(row["model_year"]))
        groups.setdefault(key, []).append(row)

    decisions = []
    for (make, canonical_model, model_year), group_rows in sorted(groups.items()):
        complaints = [row for row in group_rows if row["endpoint"] == "complaints"]
        recalls = [row for row in group_rows if row["endpoint"] == "recalls"]

        best_complaints = max(
            complaints,
            key=lambda row: (int(row["count"]), 1 if int(row["http_status"]) == 200 else 0),
            default=None,
        )
        best_recalls = max(
            recalls,
            key=lambda row: (int(row["count"]), 1 if int(row["http_status"]) == 200 else 0),
            default=None,
        )

        canonical_rows = [row for row in group_rows if row["candidate_model"] == canonical_model]
        canonical_complaints = next(
            (row for row in canonical_rows if row["endpoint"] == "complaints"), None
        )
        canonical_recalls = next((row for row in canonical_rows if row["endpoint"] == "recalls"), None)

        decisions.append(
            {
                "make": make,
                "canonical_model": canonical_model,
                "model_year": model_year,
                "recommended_complaints_model": (
                    best_complaints["candidate_model"] if best_complaints else ""
                ),
                "recommended_complaints_count": int(best_complaints["count"])
                if best_complaints
                else 0,
                "recommended_recalls_model": best_recalls["candidate_model"] if best_recalls else "",
                "recommended_recalls_count": int(best_recalls["count"]) if best_recalls else 0,
                "canonical_complaints_count": int(canonical_complaints["count"])
                if canonical_complaints
                else 0,
                "canonical_complaints_status": canonical_complaints["http_status"]
                if canonical_complaints
                else "",
                "canonical_recalls_count": int(canonical_recalls["count"]) if canonical_recalls else 0,
                "canonical_recalls_status": canonical_recalls["http_status"] if canonical_recalls else "",
            }
        )

    return {
        "row_count": len(rows),
        "checked_vehicle_count": len(groups),
        "decisions": decisions,
    }


def write_markdown_report(summary: dict[str, Any], csv_path: Path, report_path: Path) -> None:
    lines = [
        "# Model Alias Check Results",
        "",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Output CSV: `{csv_path.relative_to(PROJECT_ROOT)}`",
        f"- Checked vehicle-years: `{summary['checked_vehicle_count']}`",
        "",
        "## Recommended Query Models",
        "",
        "| Make | Canonical | Year | Complaints Query | Complaints Count | Recalls Query | Recalls Count | Canonical Complaints | Canonical Recalls |",
        "|---|---|---:|---|---:|---|---:|---:|---:|",
    ]

    for item in summary["decisions"]:
        lines.append(
            f"| {item['make']} | {item['canonical_model']} | {item['model_year']} "
            f"| {item['recommended_complaints_model']} | {item['recommended_complaints_count']} "
            f"| {item['recommended_recalls_model']} | {item['recommended_recalls_count']} "
            f"| {item['canonical_complaints_count']} | {item['canonical_recalls_count']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- 이 파일은 backfill 전에 모델명 alias가 필요한지 확인하기 위한 샘플 검사다.",
            "- `canonical complaints`가 0인데 다른 alias에서 complaints가 나오면 alias 매핑이 필요하다.",
            "- `canonical complaints`와 다른 alias가 모두 0이면 alias 문제가 아니라 NHTSA endpoint 쿼리 범위/데이터 이슈일 수 있다.",
            "- backfill collector에서는 실패/empty 결과도 반드시 로그로 남겨야 한다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check NHTSA model alias candidates.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)

    all_rows: list[dict[str, Any]] = []
    for check in config["checks"]:
        make = str(check["make"]).strip().upper()
        canonical_model = str(check["canonical_model"]).strip().upper()
        model_year = int(check["model_year"])
        candidates = [str(candidate).strip().upper() for candidate in check["candidates"]]

        for candidate in candidates:
            print(f"Checking {make} {candidate} {model_year}...", flush=True)
            candidate_rows = check_candidate(make, canonical_model, model_year, candidate)
            all_rows.extend(candidate_rows)
            counts = {row["endpoint"]: row["count"] for row in candidate_rows}
            statuses = {row["endpoint"]: row["http_status"] for row in candidate_rows}
            print(
                f"  complaints={counts.get('complaints')}({statuses.get('complaints')}) "
                f"recalls={counts.get('recalls')}({statuses.get('recalls')})",
                flush=True,
            )

    output_csv = INTERIM_DIR / "model_alias_check.csv"
    write_csv(output_csv, all_rows)

    summary = summarize(all_rows)
    summary["built_at_utc"] = datetime.now(UTC).isoformat()
    summary["config"] = str(config_path.relative_to(PROJECT_ROOT))
    summary["output_csv"] = str(output_csv.relative_to(PROJECT_ROOT))

    summary_path = INTERIM_DIR / "model_alias_check_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "model_alias_check_latest.md"
    write_markdown_report(summary, output_csv, report_path)

    docs_result_path = DOCS_DIR / "MODEL_ALIAS_RESULTS.md"
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

