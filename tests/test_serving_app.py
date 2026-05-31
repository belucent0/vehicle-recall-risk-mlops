from __future__ import annotations

from fastapi.testclient import TestClient

from recall_risk.serving import app as serving_app


def test_health() -> None:
    client = TestClient(serving_app.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_risk_scores_uses_query_params(monkeypatch) -> None:
    def fake_fetch_latest_risk_scores(
        *,
        limit: int = 25,
        make: str | None = None,
        model: str | None = None,
        component: str | None = None,
    ) -> list[dict[str, object]]:
        assert limit == 2
        assert make == "FORD"
        assert model is None
        assert component == "ENGINE"
        return [
            {
                "load_run_id": "test_load",
                "source_run_id": "test_source",
                "model_version": "rule_baseline_v1",
                "scoring_method": "complaint_spike_rule",
                "scored_at_utc": "2026-05-31T11:38:41Z",
                "rank": 1,
                "make": "FORD",
                "model": "BRONCO SPORT",
                "model_year": 2022,
                "component": "ENGINE",
                "week_start": "2026-05-11",
                "complaint_count": 1,
                "severe_complaint_count": 0,
                "complaint_spike_z": 2.0,
                "baseline_risk_score": 2.4749,
            }
        ]

    monkeypatch.setattr(serving_app, "fetch_latest_risk_scores", fake_fetch_latest_risk_scores)
    client = TestClient(serving_app.app)

    response = client.get("/risk-scores/latest?limit=2&make=FORD&component=ENGINE")

    assert response.status_code == 200
    assert response.json() == [
        {
            "load_run_id": "test_load",
            "source_run_id": "test_source",
            "model_version": "rule_baseline_v1",
            "scoring_method": "complaint_spike_rule",
            "scored_at_utc": "2026-05-31T11:38:41Z",
            "rank": 1,
            "make": "FORD",
            "model": "BRONCO SPORT",
            "model_year": 2022,
            "component": "ENGINE",
            "week_start": "2026-05-11",
            "complaint_count": 1,
            "severe_complaint_count": 0,
            "complaint_spike_z": 2.0,
            "baseline_risk_score": 2.4749,
        }
    ]
