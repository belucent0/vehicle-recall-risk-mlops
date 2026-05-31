from __future__ import annotations

from datetime import date
from datetime import datetime

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from psycopg import Error as PsycopgError
from pydantic import BaseModel
from pydantic import Field

from recall_risk.storage.postgres import fetch_latest_risk_scores
from recall_risk.storage.postgres import fetch_model_latest_risk_scores
from recall_risk.storage.postgres import ping_database

app = FastAPI(title="Vehicle Recall Risk API")


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class RiskScoreResponse(BaseModel):
    load_run_id: str | None = None
    source_run_id: str | None = None
    model_version: str | None = None
    scoring_method: str | None = None
    scored_at_utc: datetime | None = None
    rank: int | None
    make: str
    model: str
    model_year: int | None
    component: str | None
    week_start: date | None
    complaint_count: int | None
    severe_complaint_count: int | None
    complaint_spike_z: float | None
    baseline_risk_score: float | None = Field(
        description="Complaint spike score. This is not a calibrated recall probability."
    )


class ModelRiskScoreResponse(BaseModel):
    load_run_id: str | None = None
    source_run_id: str | None = None
    model_version: str | None = None
    model_type: str | None = None
    model_library: str | None = None
    scoring_method: str | None = None
    scored_at_utc: datetime | None = None
    rank: int | None
    make: str
    model: str
    model_year: int | None
    component: str | None
    week_start: date | None
    complaint_count: int | None
    severe_complaint_count: int | None
    complaint_spike_z: float | None
    baseline_risk_score: float | None = Field(
        description="Rule baseline complaint spike score used as an input feature."
    )
    logistic_risk_score: float | None = Field(
        description="scikit-learn logistic model score. Not yet calibrated as a recall probability."
    )


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/db")
def health_db() -> DatabaseHealthResponse:
    try:
        ping_database()
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

    return DatabaseHealthResponse(status="ok", database="postgresql")


@app.get("/risk-scores/latest")
def latest_risk_scores(
    limit: int = Query(default=25, ge=1, le=100),
    make: str | None = Query(default=None, min_length=1),
    model: str | None = Query(default=None, min_length=1),
    component: str | None = Query(default=None, min_length=1),
) -> list[RiskScoreResponse]:
    try:
        rows = fetch_latest_risk_scores(
            limit=limit,
            make=make,
            model=model,
            component=component,
        )
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

    return [RiskScoreResponse(**row) for row in rows]


@app.get("/risk-scores/model/latest")
def model_latest_risk_scores(
    limit: int = Query(default=25, ge=1, le=100),
    make: str | None = Query(default=None, min_length=1),
    model: str | None = Query(default=None, min_length=1),
    component: str | None = Query(default=None, min_length=1),
) -> list[ModelRiskScoreResponse]:
    try:
        rows = fetch_model_latest_risk_scores(
            limit=limit,
            make=make,
            model=model,
            component=component,
        )
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

    return [ModelRiskScoreResponse(**row) for row in rows]
