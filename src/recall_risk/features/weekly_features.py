from __future__ import annotations

import csv
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


WEEKLY_FEATURE_COLUMNS = [
    "make",
    "model",
    "model_year",
    "component_primary",
    "week_start",
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
]

RISK_SCORE_COLUMNS = [
    "rank",
    "make",
    "model",
    "model_year",
    "component_primary",
    "week_start",
    "complaint_count",
    "crash_count",
    "fire_count",
    "injury_count",
    "death_count",
    "severe_complaint_count",
    "rolling_8w_complaint_mean_prior",
    "complaint_spike_z",
    "baseline_risk_score",
]


@dataclass(frozen=True)
class EntityKey:
    make: str
    model: str
    model_year: str
    component_primary: str


def parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def parse_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


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


def daterange_weeks(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current = current + timedelta(days=7)


def aggregate_weekly_complaints(complaints: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Aggregate normalized complaints to entity-week rows.

    The output is dense per entity between that entity's first and last observed
    complaint week. Missing weeks get zero counts so rolling features use real
    time gaps instead of only observed complaint weeks.
    """

    aggregates: dict[tuple[EntityKey, date], dict[str, Any]] = {}
    entity_minmax: dict[EntityKey, list[date]] = {}

    for row in complaints:
        filed_date = parse_iso_date(row.get("date_complaint_filed", ""))
        if filed_date is None:
            continue

        component_primary = (row.get("component_primary") or "UNKNOWN").strip().upper()
        key = EntityKey(
            make=(row.get("make") or "").strip().upper(),
            model=(row.get("model") or "").strip().upper(),
            model_year=str(row.get("model_year") or "").strip(),
            component_primary=component_primary,
        )
        if not key.make or not key.model or not key.model_year or not key.component_primary:
            continue

        wk = week_start(filed_date)
        entity_minmax.setdefault(key, [wk, wk])
        entity_minmax[key][0] = min(entity_minmax[key][0], wk)
        entity_minmax[key][1] = max(entity_minmax[key][1], wk)

        item = aggregates.setdefault(
            (key, wk),
            {
                "make": key.make,
                "model": key.model,
                "model_year": key.model_year,
                "component_primary": key.component_primary,
                "week_start": wk.isoformat(),
                "complaint_count": 0,
                "crash_count": 0,
                "fire_count": 0,
                "injury_count": 0,
                "death_count": 0,
                "severe_complaint_count": 0,
            },
        )

        injury_count = parse_int(row.get("number_of_injuries"))
        death_count = parse_int(row.get("number_of_deaths"))
        crash = parse_bool(row.get("crash"))
        fire = parse_bool(row.get("fire"))
        severe = crash or fire or injury_count > 0 or death_count > 0

        item["complaint_count"] += 1
        item["crash_count"] += int(crash)
        item["fire_count"] += int(fire)
        item["injury_count"] += injury_count
        item["death_count"] += death_count
        item["severe_complaint_count"] += int(severe)

    dense_rows: list[dict[str, Any]] = []
    for key, (min_week, max_week) in entity_minmax.items():
        for wk in daterange_weeks(min_week, max_week):
            dense_rows.append(
                aggregates.get(
                    (key, wk),
                    {
                        "make": key.make,
                        "model": key.model,
                        "model_year": key.model_year,
                        "component_primary": key.component_primary,
                        "week_start": wk.isoformat(),
                        "complaint_count": 0,
                        "crash_count": 0,
                        "fire_count": 0,
                        "injury_count": 0,
                        "death_count": 0,
                        "severe_complaint_count": 0,
                    },
                )
            )

    dense_rows.sort(
        key=lambda row: (
            row["make"],
            row["model"],
            row["model_year"],
            row["component_primary"],
            row["week_start"],
        )
    )
    return dense_rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def add_rolling_features(weekly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in weekly_rows:
        grouped[
            (
                row["make"],
                row["model"],
                row["model_year"],
                row["component_primary"],
            )
        ].append(row)

    output: list[dict[str, Any]] = []
    for _, rows in grouped.items():
        rows.sort(key=lambda row: row["week_start"])
        history: deque[int] = deque(maxlen=8)

        for row in rows:
            history_values = list(history)
            last_4 = history_values[-4:]
            last_8 = history_values[-8:]

            rolling_4w_mean = mean([float(v) for v in last_4])
            rolling_8w_mean = mean([float(v) for v in last_8])
            rolling_8w_std = sample_std([float(v) for v in last_8])

            complaint_count = parse_int(row["complaint_count"])
            spike_z = 0.0
            if rolling_8w_std > 0:
                spike_z = (complaint_count - rolling_8w_mean) / rolling_8w_std

            # A deliberately simple baseline: non-negative spike + mild severe-event boost.
            severe_boost = 0.5 * parse_int(row["severe_complaint_count"])
            risk_score = max(0.0, spike_z) + severe_boost

            enriched = dict(row)
            enriched["rolling_4w_complaint_mean_prior"] = round(rolling_4w_mean, 4)
            enriched["rolling_8w_complaint_mean_prior"] = round(rolling_8w_mean, 4)
            enriched["rolling_8w_complaint_std_prior"] = round(rolling_8w_std, 4)
            enriched["complaint_spike_z"] = round(spike_z, 4)
            enriched["baseline_risk_score"] = round(risk_score, 4)
            output.append(enriched)

            history.append(complaint_count)

    output.sort(
        key=lambda row: (
            row["week_start"],
            row["make"],
            row["model"],
            row["model_year"],
            row["component_primary"],
        )
    )
    return output


def latest_week_scores(feature_rows: list[dict[str, Any]], top_k: int = 25) -> list[dict[str, Any]]:
    if not feature_rows:
        return []
    latest_week = max(row["week_start"] for row in feature_rows)
    rows = [row for row in feature_rows if row["week_start"] == latest_week]
    rows.sort(key=lambda row: float(row["baseline_risk_score"]), reverse=True)

    output = []
    for idx, row in enumerate(rows[:top_k], start=1):
        item = {column: row.get(column, "") for column in RISK_SCORE_COLUMNS}
        item["rank"] = idx
        output.append(item)
    return output

