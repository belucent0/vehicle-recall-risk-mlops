from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


COMPLAINT_COLUMNS = [
    "source",
    "odi_number",
    "make",
    "model",
    "model_year",
    "manufacturer",
    "components",
    "component_primary",
    "date_complaint_filed",
    "date_of_incident",
    "crash",
    "fire",
    "number_of_injuries",
    "number_of_deaths",
    "vin_prefix",
    "summary",
    "summary_length",
]

RECALL_COLUMNS = [
    "source",
    "nhtsa_campaign_number",
    "make",
    "model",
    "model_year",
    "manufacturer",
    "component",
    "component_primary",
    "report_received_date",
    "park_it",
    "park_outside",
    "over_the_air_update",
    "summary",
    "consequence",
    "remedy",
    "notes",
    "summary_length",
]


def parse_nhtsa_date(value: Any) -> str:
    """Parse NHTSA MM/DD/YYYY date values to ISO date.

    Returns an empty string when parsing fails so CSV outputs stay simple.
    """

    if value in (None, ""):
        return ""
    value = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def as_int(value: Any) -> int | str:
    if value in (None, ""):
        return ""
    try:
        return int(value)
    except (TypeError, ValueError):
        return ""


def as_bool(value: Any) -> bool | str:
    if value in (None, ""):
        return ""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return ""


def split_components(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(split_components(item))
        return parts
    text = str(value)
    return [part.strip().upper() for part in text.split(",") if part.strip()]


def primary_component(value: Any) -> str:
    parts = split_components(value)
    return parts[0] if parts else ""


def normalize_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return " ".join(str(value).split())


def first_vehicle_product(record: dict[str, Any]) -> dict[str, Any]:
    products = record.get("products") or []
    if not isinstance(products, list):
        return {}
    for product in products:
        if isinstance(product, dict) and str(product.get("type", "")).lower() == "vehicle":
            return product
    return products[0] if products and isinstance(products[0], dict) else {}


def normalize_complaint(record: dict[str, Any]) -> dict[str, Any]:
    product = first_vehicle_product(record)
    components = normalize_text(record.get("components"))
    summary = normalize_text(record.get("summary"))

    return {
        "source": "nhtsa_complaints",
        "odi_number": str(record.get("odiNumber") or ""),
        "make": str(product.get("productMake") or "").upper(),
        "model": str(product.get("productModel") or "").upper(),
        "model_year": as_int(product.get("productYear")),
        "manufacturer": normalize_text(record.get("manufacturer") or product.get("manufacturer")),
        "components": components,
        "component_primary": primary_component(components),
        "date_complaint_filed": parse_nhtsa_date(record.get("dateComplaintFiled")),
        "date_of_incident": parse_nhtsa_date(record.get("dateOfIncident")),
        "crash": as_bool(record.get("crash")),
        "fire": as_bool(record.get("fire")),
        "number_of_injuries": as_int(record.get("numberOfInjuries")),
        "number_of_deaths": as_int(record.get("numberOfDeaths")),
        "vin_prefix": str(record.get("vin") or "")[:11].upper(),
        "summary": summary,
        "summary_length": len(summary),
    }


def normalize_recall(record: dict[str, Any]) -> dict[str, Any]:
    component = normalize_text(record.get("Component"))
    summary = normalize_text(record.get("Summary"))

    return {
        "source": "nhtsa_recalls",
        "nhtsa_campaign_number": str(record.get("NHTSACampaignNumber") or ""),
        "make": str(record.get("Make") or "").upper(),
        "model": str(record.get("Model") or "").upper(),
        "model_year": as_int(record.get("ModelYear")),
        "manufacturer": normalize_text(record.get("Manufacturer")),
        "component": component,
        "component_primary": primary_component(component),
        "report_received_date": parse_nhtsa_date(record.get("ReportReceivedDate")),
        "park_it": as_bool(record.get("parkIt")),
        "park_outside": as_bool(record.get("parkOutSide")),
        "over_the_air_update": as_bool(record.get("overTheAirUpdate")),
        "summary": summary,
        "consequence": normalize_text(record.get("Consequence")),
        "remedy": normalize_text(record.get("Remedy")),
        "notes": normalize_text(record.get("Notes")),
        "summary_length": len(summary),
    }


def read_nhtsa_results(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results") or payload.get("Results") or []
    if not isinstance(results, list):
        raise ValueError(f"Unexpected results shape in {path}: {type(results)}")
    return [item for item in results if isinstance(item, dict)]


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def summarize_rows(rows: list[dict[str, Any]], date_col: str, component_col: str) -> dict[str, Any]:
    dates = [row[date_col] for row in rows if row.get(date_col)]
    components = Counter(row.get(component_col) or "" for row in rows)
    components.pop("", None)
    return {
        "row_count": len(rows),
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
        "top_components": components.most_common(10),
    }

