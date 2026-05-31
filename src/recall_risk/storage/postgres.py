from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def database_url_from_env() -> str:
    """Build the PostgreSQL connection URL from environment variables."""

    if database_url := os.getenv("DATABASE_URL"):
        return database_url

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "55432")
    database = os.getenv("POSTGRES_DB", "recall_risk")
    user = os.getenv("POSTGRES_USER", "recall_user")
    password = os.getenv("POSTGRES_PASSWORD", "recall_password")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def ping_database() -> bool:
    """Return True when PostgreSQL is reachable."""

    with psycopg.connect(database_url_from_env(), connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1


def fetch_latest_risk_scores(
    *,
    limit: int = 25,
    make: str | None = None,
    model: str | None = None,
    component: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch latest risk scores from the typed PostgreSQL view."""

    params: dict[str, Any] = {"limit": limit}
    conditions: list[sql.Composable] = []

    if make:
        conditions.append(sql.SQL("make = %(make)s"))
        params["make"] = make.strip().upper()

    if model:
        conditions.append(sql.SQL("model = %(model)s"))
        params["model"] = model.strip().upper()

    if component:
        conditions.append(sql.SQL("component_primary ILIKE %(component)s"))
        params["component"] = f"%{component.strip()}%"

    where_clause = sql.SQL("")
    if conditions:
        where_clause = sql.SQL("WHERE ") + sql.SQL(" AND ").join(conditions)

    query = sql.SQL(
        """
        SELECT
            load_run_id,
            source_run_id,
            model_version,
            scoring_method,
            scored_at_utc,
            rank,
            make,
            model,
            model_year,
            component_primary AS component,
            week_start,
            complaint_count,
            severe_complaint_count,
            complaint_spike_z,
            baseline_risk_score
        FROM recall_risk.v_latest_risk_scores
        {where_clause}
        ORDER BY rank ASC
        LIMIT %(limit)s
        """
    ).format(where_clause=where_clause)

    with psycopg.connect(database_url_from_env(), row_factory=dict_row, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
