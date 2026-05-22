from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


TRAINING_DATASET_COLUMNS = [
    "make",
    "model",
    "model_year",
    "component_primary",
    "component_family",
    "week_start",
    "as_of_date",
    "label_observation_end_date",
    "complaint_count",
    "crash_count",
    "fire_count",
    "injury_count",
    "death_count",
    "severe_complaint_count",
    "rolling_4w_complaint_mean_prior",
    "rolling_8w_complaint_mean_prior",
    "rolling_8w_complaint_std_prior",
    "complaint_spike_z",
    "baseline_risk_score",
    "label_available",
    "next_90d_recall",
    "recall_count_90d",
    "days_to_first_recall",
    "first_recall_date_90d",
    "matched_campaign_numbers",
    "matched_recall_components",
]


def parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def coerce_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return parse_iso_date(value)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def component_family(value: str) -> str:
    """Map detailed NHTSA component text to a coarse component family.

    Examples:
    - ELECTRICAL SYSTEM:SOFTWARE -> ELECTRICAL SYSTEM
    - FUEL SYSTEM, GASOLINE:DELIVERY -> FUEL SYSTEM
    - POWER TRAIN:AUTOMATIC TRANSMISSION -> POWER TRAIN
    """

    text = (value or "").strip().upper()
    if not text:
        return ""
    text = text.split(",", maxsplit=1)[0]
    text = text.split(":", maxsplit=1)[0]
    return " ".join(text.split())


def make_entity_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("make") or "").strip().upper(),
        str(row.get("model") or "").strip().upper(),
        str(row.get("model_year") or "").strip(),
        component_family(str(row.get("component_primary") or row.get("component") or "")),
    )


def build_recall_index(
    recall_rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str, str, str], list[dict[str, Any]]], date | None]:
    index: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    max_recall_date: date | None = None

    for row in recall_rows:
        recall_date = parse_iso_date(row.get("report_received_date", ""))
        if recall_date is None:
            continue

        key = make_entity_key(row)
        if not all(key):
            continue

        max_recall_date = recall_date if max_recall_date is None else max(max_recall_date, recall_date)
        index[key].append(
            {
                "recall_date": recall_date,
                "campaign_number": row.get("nhtsa_campaign_number", ""),
                "component": row.get("component", ""),
                "component_family": key[3],
            }
        )

    for recalls in index.values():
        recalls.sort(key=lambda item: item["recall_date"])

    return index, max_recall_date


def add_recall_labels(
    feature_rows: list[dict[str, str]],
    recall_rows: list[dict[str, str]],
    horizon_days: int = 90,
    data_as_of_date: str | date | None = None,
) -> list[dict[str, Any]]:
    recall_index, max_recall_date = build_recall_index(recall_rows)
    data_as_of = coerce_date(data_as_of_date)

    if max_recall_date is None and data_as_of is None:
        label_observation_end_date = None
    elif max_recall_date is None:
        label_observation_end_date = data_as_of
    elif data_as_of is None:
        label_observation_end_date = max_recall_date
    else:
        # If the source contains future-dated recall records, do not let them
        # make labels available beyond the actual data-as-of date.
        label_observation_end_date = min(max_recall_date, data_as_of)

    labeled_rows: list[dict[str, Any]] = []

    for row in feature_rows:
        week = parse_iso_date(row.get("week_start", ""))
        if week is None:
            continue

        # Features for a weekly row are assumed available at end of that week.
        as_of_date = week + timedelta(days=6)
        window_end = as_of_date + timedelta(days=horizon_days)
        key = make_entity_key(row)
        recalls = recall_index.get(key, [])
        matches = [
            item
            for item in recalls
            if as_of_date < item["recall_date"] <= window_end
            and (
                label_observation_end_date is None
                or item["recall_date"] <= label_observation_end_date
            )
        ]

        label_available = (
            label_observation_end_date is not None
            and window_end <= label_observation_end_date
        )
        first_recall_date = min((item["recall_date"] for item in matches), default=None)

        output = dict(row)
        output["component_family"] = key[3]
        output["as_of_date"] = as_of_date.isoformat()
        output["label_observation_end_date"] = (
            label_observation_end_date.isoformat() if label_observation_end_date else ""
        )
        output["label_available"] = int(label_available)

        if label_available:
            output["next_90d_recall"] = int(bool(matches))
            output["recall_count_90d"] = len(matches)
            output["days_to_first_recall"] = (
                (first_recall_date - as_of_date).days if first_recall_date is not None else ""
            )
            output["first_recall_date_90d"] = (
                first_recall_date.isoformat() if first_recall_date is not None else ""
            )
            output["matched_campaign_numbers"] = "|".join(
                sorted({item["campaign_number"] for item in matches if item["campaign_number"]})
            )
            output["matched_recall_components"] = "|".join(
                sorted({item["component"] for item in matches if item["component"]})
            )
        else:
            output["next_90d_recall"] = ""
            output["recall_count_90d"] = ""
            output["days_to_first_recall"] = ""
            output["first_recall_date_90d"] = ""
            output["matched_campaign_numbers"] = ""
            output["matched_recall_components"] = ""

        labeled_rows.append(output)

    return labeled_rows


def summarize_labeled_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = [row for row in rows if str(row.get("label_available")) == "1"]
    positives = [row for row in available if str(row.get("next_90d_recall")) == "1"]
    positive_entities = {
        (
            row.get("make"),
            row.get("model"),
            row.get("model_year"),
            row.get("component_family"),
        )
        for row in positives
    }

    positive_components = Counter(row.get("component_family") or "" for row in positives)
    positive_components.pop("", None)

    max_as_of = max((row.get("as_of_date") for row in rows), default="")
    max_labeled_as_of = max((row.get("as_of_date") for row in available), default="")

    return {
        "row_count": len(rows),
        "label_available_count": len(available),
        "label_unavailable_count": len(rows) - len(available),
        "positive_count": len(positives),
        "negative_count": len(available) - len(positives),
        "positive_rate": round(len(positives) / len(available), 6) if available else 0,
        "positive_entity_count": len(positive_entities),
        "max_as_of_date": max_as_of,
        "max_labeled_as_of_date": max_labeled_as_of,
        "top_positive_components": positive_components.most_common(10),
    }
