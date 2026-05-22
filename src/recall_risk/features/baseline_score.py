from __future__ import annotations

import pandas as pd


def add_complaint_spike_score(
    weekly: pd.DataFrame,
    count_col: str = "complaint_count",
    window: int = 8,
) -> pd.DataFrame:
    """Add a simple rolling z-score based risk signal.

    Expected columns:
    - make
    - model
    - model_year
    - component
    - week
    - complaint_count
    """

    keys = ["make", "model", "model_year", "component"]
    weekly = weekly.sort_values(keys + ["week"]).copy()

    grouped = weekly.groupby(keys, dropna=False)[count_col]
    rolling_mean = grouped.transform(lambda s: s.shift(1).rolling(window, min_periods=3).mean())
    rolling_std = grouped.transform(lambda s: s.shift(1).rolling(window, min_periods=3).std())

    weekly["complaint_rolling_mean"] = rolling_mean
    weekly["complaint_rolling_std"] = rolling_std
    weekly["complaint_spike_z"] = (
        (weekly[count_col] - rolling_mean) / rolling_std.replace(0, pd.NA)
    ).fillna(0.0)
    weekly["baseline_risk_score"] = weekly["complaint_spike_z"].clip(lower=0)
    return weekly

