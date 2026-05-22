from __future__ import annotations

import pandas as pd

from recall_risk.features.baseline_score import add_complaint_spike_score


def test_add_complaint_spike_score_adds_columns() -> None:
    weekly = pd.DataFrame(
        {
            "make": ["HYUNDAI"] * 10,
            "model": ["SANTA FE"] * 10,
            "model_year": [2022] * 10,
            "component": ["ELECTRICAL SYSTEM"] * 10,
            "week": pd.date_range("2024-01-01", periods=10, freq="W"),
            "complaint_count": [1, 1, 1, 1, 1, 1, 1, 1, 5, 8],
        }
    )

    scored = add_complaint_spike_score(weekly)

    assert "complaint_spike_z" in scored.columns
    assert "baseline_risk_score" in scored.columns

