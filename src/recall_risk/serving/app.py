from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from psycopg import Error as PsycopgError
from pydantic import BaseModel
from pydantic import Field

from recall_risk.storage.postgres import fetch_latest_risk_scores
from recall_risk.storage.postgres import ping_database

app = FastAPI(title="NHTSA Recall Risk API")


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class RiskScoreResponse(BaseModel):
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

