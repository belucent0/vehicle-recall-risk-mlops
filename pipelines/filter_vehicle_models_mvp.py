from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "interim" / "vehicle_models.csv"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


BASE_COLUMNS = [
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

OUTPUT_COLUMNS = BASE_COLUMNS + ["mvp_include_reason"]
EXCLUDED_COLUMNS = BASE_COLUMNS + ["exclude_reason"]


MVP_MODEL_WHITELIST = {
    "FORD": {
        "BRONCO",
        "BRONCO SPORT",
        "C-MAX",
        "ECOSPORT",
        "EDGE",
        "ESCAPE",
        "EXPEDITION",
        "EXPEDITION EL",
        "EXPEDITION MAX",
        "EXPLORER",
        "F-150",
        "F-250",
        "F-350",
        "F-450",
        "F-550",
        "F-600",
        "F-650",
        "F-750",
        "FIESTA",
        "FLEX",
        "FOCUS",
        "FUSION",
        "GT",
        "GT MKII",
        "MAVERICK",
        "MUSTANG",
        "MUSTANG GTD",
        "MUSTANG MACH-E",
        "RANGER",
        "TAURUS",
        "TRANSIT",
        "TRANSIT CONNECT",
        "E-350",
        "E-450",
        "E-550",
    },
    "HYUNDAI": {
        "ACCENT",
        "AZERA",
        "ELANTRA",
        "ELANTRA GT",
        "ELANTRA N",
        "EQUUS",
        "GENESIS",
        "GENESIS COUPE",
        "IONIQ",
        "IONIQ 5",
        "IONIQ 5 N",
        "IONIQ 6",
        "IONIQ 6 N",
        "IONIQ 9",
        "KONA",
        "KONA N",
        "NEXO",
        "PALISADE",
        "SANTA CRUZ",
        "SANTA FE",
        "SANTA FE SPORT",
        "SANTA FE XL",
        "SONATA",
        "TUCSON",
        "VELOSTER",
        "VELOSTER N",
        "VENUE",
    },
    "KIA": {
        "CADENZA",
        "CARNIVAL",
        "EV6",
        "EV9",
        "FORTE",
        "FORTE KOUP",
        "K4",
        "K5",
        "K900",
        "NIRO",
        "OPTIMA",
        "RIO",
        "RONDO",
        "SEDONA",
        "SELTOS",
        "SORENTO",
        "SOUL",
        "SPORTAGE",
        "STINGER",
        "TELLURIDE",
    },
    "TESLA": {
        "CYBERTRUCK",
        "MODEL 3",
        "MODEL S",
        "MODEL X",
        "MODEL Y",
    },
    "TOYOTA": {
        "4RUNNER",
        "86",
        "AVALON",
        "BZ",
        "BZ WOODLAND",
        "BZ4X",
        "C-HR",
        "CAMRY",
        "COROLLA",
        "COROLLA CROSS",
        "COROLLA IM",
        "CROWN",
        "CROWN SIGNIA",
        "GR COROLLA",
        "GR86",
        "GRAND HIGHLANDER",
        "HIGHLANDER",
        "LAND CRUISER",
        "MIRAI",
        "PRIUS",
        "PRIUS C",
        "PRIUS PRIME (PHEV)",
        "PRIUS V",
        "RAV4",
        "RAV4 PRIME (PHEV)",
        "SCION FR-S",
        "SCION IA",
        "SCION IM",
        "SCION IQ",
        "SCION TC",
        "SCION XB",
        "SEQUOIA",
        "SIENNA",
        "SUPRA",
        "TACOMA",
        "TUNDRA",
        "VENZA",
        "YARIS",
        "YARIS IA",
    },
}


def normalize_model_name(value: str) -> str:
    text = (value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def canonical_set(values: set[str]) -> set[str]:
    return {normalize_model_name(value) for value in values}


MVP_MODEL_WHITELIST_NORMALIZED = {
    make: canonical_set(models) for make, models in MVP_MODEL_WHITELIST.items()
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def classify_row(row: dict[str, str]) -> tuple[bool, str]:
    make = (row.get("make_query") or row.get("make_name") or "").strip().upper()
    model = row.get("model_name") or ""
    model_norm = normalize_model_name(model)

    if make not in MVP_MODEL_WHITELIST_NORMALIZED:
        return False, "make_not_in_mvp_scope"
    if model_norm in MVP_MODEL_WHITELIST_NORMALIZED[make]:
        return True, "make_model_whitelist"
    return False, "model_not_in_mvp_whitelist"


def filter_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included = []
    excluded = []

    for row in rows:
        # Ensure normalized name is present and consistent.
        normalized = normalize_model_name(row.get("model_name", ""))
        row = dict(row)
        row["model_name_normalized"] = normalized

        include, reason = classify_row(row)
        if include:
            row["mvp_include_reason"] = reason
            included.append(row)
        else:
            row["exclude_reason"] = reason
            excluded.append(row)

    included.sort(key=lambda r: (r["make_query"], int(r["model_year"]), r["model_name_normalized"]))
    excluded.sort(key=lambda r: (r["make_query"], int(r["model_year"]), r["model_name_normalized"]))
    return included, excluded


def summarize(included: list[dict[str, Any]], excluded: list[dict[str, Any]]) -> dict[str, Any]:
    by_make = Counter(row["make_query"] for row in included)
    by_year = Counter(str(row["model_year"]) for row in included)
    excluded_by_reason = Counter(row["exclude_reason"] for row in excluded)
    excluded_by_make = Counter(row["make_query"] for row in excluded)

    unique_included_by_make: dict[str, set[str]] = defaultdict(set)
    unique_excluded_by_make: dict[str, set[str]] = defaultdict(set)
    for row in included:
        unique_included_by_make[row["make_query"]].add(row["model_name_normalized"])
    for row in excluded:
        unique_excluded_by_make[row["make_query"]].add(row["model_name_normalized"])

    sample_excluded = [
        {
            "make": row["make_query"],
            "model": row["model_name"],
            "model_year": row["model_year"],
            "reason": row["exclude_reason"],
        }
        for row in excluded[:40]
    ]

    return {
        "input_row_count": len(included) + len(excluded),
        "included_row_count": len(included),
        "excluded_row_count": len(excluded),
        "included_by_make": dict(sorted(by_make.items())),
        "included_by_year": dict(sorted(by_year.items())),
        "unique_included_model_count_by_make": {
            make: len(models) for make, models in sorted(unique_included_by_make.items())
        },
        "unique_excluded_model_count_by_make": {
            make: len(models) for make, models in sorted(unique_excluded_by_make.items())
        },
        "excluded_by_reason": dict(sorted(excluded_by_reason.items())),
        "excluded_by_make": dict(sorted(excluded_by_make.items())),
        "sample_excluded": sample_excluded,
    }


def write_markdown_report(
    summary: dict[str, Any],
    included_path: Path,
    excluded_path: Path,
    report_path: Path,
) -> None:
    lines = [
        "# Vehicle Model Filter Results",
        "",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Input rows: `{summary['input_row_count']}`",
        f"- Included rows: `{summary['included_row_count']}`",
        f"- Excluded rows: `{summary['excluded_row_count']}`",
        f"- Included CSV: `{included_path.relative_to(PROJECT_ROOT)}`",
        f"- Excluded CSV: `{excluded_path.relative_to(PROJECT_ROOT)}`",
        "",
        "## Included by Make",
        "",
        "| Make | Rows | Unique included models |",
        "|---|---:|---:|",
    ]

    for make, count in summary["included_by_make"].items():
        unique_count = summary["unique_included_model_count_by_make"].get(make, 0)
        lines.append(f"| {make} | {count} | {unique_count} |")

    lines.extend(["", "## Included by Year", "", "| Year | Rows |", "|---:|---:|"])
    for year, count in summary["included_by_year"].items():
        lines.append(f"| {year} | {count} |")

    lines.extend(["", "## Excluded by Reason", "", "| Reason | Rows |", "|---|---:|"])
    for reason, count in summary["excluded_by_reason"].items():
        lines.append(f"| {reason} | {count} |")

    lines.extend(["", "## Excluded by Make", "", "| Make | Rows | Unique excluded models |", "|---|---:|---:|"])
    for make, count in summary["excluded_by_make"].items():
        unique_count = summary["unique_excluded_model_count_by_make"].get(make, 0)
        lines.append(f"| {make} | {count} | {unique_count} |")

    lines.extend(
        [
            "",
            "## Sample Excluded Rows",
            "",
            "| Make | Model | Year | Reason |",
            "|---|---|---:|---|",
        ]
    )
    for row in summary["sample_excluded"]:
        lines.append(f"| {row['make']} | {row['model']} | {row['model_year']} | {row['reason']} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- MVP에서는 VPIC 전체 모델 목록을 그대로 쓰지 않고, 제조사별 대표 차량 모델 whitelist를 사용한다.",
            "- 목적은 모델링 이전에 불필요한 empty API 요청을 줄이는 것이다.",
            "- 이 필터는 최종 데이터 품질 규칙이 아니라 MVP 수집 후보를 만들기 위한 1차 규칙이다.",
            "- 다음 단계에서는 `vehicle_models_mvp.csv`를 입력으로 backfill을 다시 실행한다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter VPIC vehicle model list for MVP backfill.")
    parser.add_argument("--input", default=str(INPUT_PATH))
    parser.add_argument("--included-output", default=str(INTERIM_DIR / "vehicle_models_mvp.csv"))
    parser.add_argument("--excluded-output", default=str(INTERIM_DIR / "vehicle_models_excluded.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    included_path = Path(args.included_output)
    excluded_path = Path(args.excluded_output)

    rows = read_csv(input_path)
    included, excluded = filter_rows(rows)
    write_csv(included_path, included, OUTPUT_COLUMNS)
    write_csv(excluded_path, excluded, EXCLUDED_COLUMNS)

    summary = summarize(included, excluded)
    summary["built_at_utc"] = datetime.now(UTC).isoformat()
    summary["input_csv"] = str(input_path.relative_to(PROJECT_ROOT))
    summary["included_csv"] = str(included_path.relative_to(PROJECT_ROOT))
    summary["excluded_csv"] = str(excluded_path.relative_to(PROJECT_ROOT))

    summary_path = INTERIM_DIR / "vehicle_model_filter_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "vehicle_model_filter_latest.md"
    write_markdown_report(summary, included_path, excluded_path, report_path)

    docs_result_path = DOCS_DIR / "VEHICLE_MODEL_FILTER_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Input rows:    {summary['input_row_count']}")
    print(f"Included rows: {summary['included_row_count']}")
    print(f"Excluded rows: {summary['excluded_row_count']}")
    print(f"Wrote:         {included_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:         {excluded_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:         {report_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:         {docs_result_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

