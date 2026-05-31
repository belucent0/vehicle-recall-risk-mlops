from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_BACKFILL_DIR = PROJECT_ROOT / "data" / "processed" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in PROCESSED_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed backfill run directory under {PROCESSED_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_project_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def split_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = sum(int(row["next_90d_recall"]) for row in rows)
    return {
        "row_count": len(rows),
        "positive_count": positives,
        "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
        "min_as_of_date": min((row["as_of_date"] for row in rows), default=""),
        "max_as_of_date": max((row["as_of_date"] for row in rows), default=""),
    }


def sample_training_rows(
    train_rows: list[dict[str, Any]],
    negative_ratio: int = 20,
    max_rows: int = 100_000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    positives = [row for row in train_rows if str(row["next_90d_recall"]) == "1"]
    negatives = [row for row in train_rows if str(row["next_90d_recall"]) == "0"]

    max_negative_by_ratio = len(positives) * negative_ratio
    max_negative_by_total = max(0, max_rows - len(positives))
    negative_count = min(len(negatives), max_negative_by_ratio, max_negative_by_total)

    rng = random.Random(seed)
    sampled_negatives = rng.sample(negatives, negative_count) if negative_count < len(negatives) else negatives
    sampled = positives + sampled_negatives
    sampled.sort(key=lambda row: (row["as_of_date"], row["make"], row["model"], row["component_family"]))
    return sampled


def top_predictions(rows: list[dict[str, Any]], score_column: str, limit: int = 20) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: float(row.get(score_column) or 0.0), reverse=True)
    output = []
    for idx, row in enumerate(sorted_rows[:limit], start=1):
        output.append(
            {
                "rank": idx,
                "make": row.get("make"),
                "model": row.get("model"),
                "model_year": row.get("model_year"),
                "component_family": row.get("component_family"),
                "as_of_date": row.get("as_of_date"),
                "label": row.get("next_90d_recall"),
                "days_to_first_recall": row.get("days_to_first_recall"),
                "score": row.get(score_column),
                "matched_campaign_numbers": row.get("matched_campaign_numbers"),
            }
        )
    return output


def metric_lines(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {metrics['row_count']} |",
        f"| Positives | {metrics['positive_count']} |",
        f"| Positive rate | {metrics['positive_rate']} |",
        f"| Average precision | {metrics['average_precision']} |",
        f"| Brier score | {metrics['brier_score']} |",
        "",
        "| K | Precision@K | Recall@K | Hits |",
        "|---:|---:|---:|---:|",
    ]
    for item in metrics["precision_recall_at_k"]:
        lines.append(f"| {item['k']} | {item['precision']} | {item['recall']} | {item['hits']} |")
    lines.append("")
    return lines


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    trained_at_utc = summary.get("trained_at_utc", summary.get("built_at_utc", ""))
    scored_at_utc = summary.get("scored_at_utc", summary.get("built_at_utc", ""))

    lines = [
        "# Backfill Baseline Model Results",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Trained at UTC: `{trained_at_utc}`",
        f"- Scored at UTC: `{scored_at_utc}`",
        f"- Split cutoff as-of date: `{summary['split']['cutoff_as_of_date']}`",
        f"- Model type: `{summary['model_type']}`",
        f"- Model version: `{summary.get('model_version', '')}`",
        f"- Logistic train sample rows: `{summary['logistic_training_sample']['row_count']}`",
        f"- Model artifact: `{summary['model_artifact']}`",
        "",
        "## Pipeline stages",
        "",
        "```text",
        "train_model_backfill.py",
        "  -> sklearn pipeline artifact",
        "  -> coefficient CSV",
        "  -> training summary JSON",
        "",
        "score_batch_backfill.py",
        "  -> load sklearn pipeline artifact",
        "  -> score held-out temporal test rows",
        "  -> prediction CSV",
        "  -> evaluation summary/report",
        "```",
        "",
        "## Split",
        "",
        "| Split | Rows | Positives | Positive rate | Date range |",
        "|---|---:|---:|---:|---|",
    ]

    for split_name in ["train", "test"]:
        item = summary["split"][split_name]
        lines.append(
            f"| {split_name} | {item['row_count']} | {item['positive_count']} "
            f"| {item['positive_rate']} | {item['min_as_of_date']} ~ {item['max_as_of_date']} |"
        )

    lines.extend(["", "## Test Metrics", ""])
    lines.extend(metric_lines("Rule baseline: baseline_risk_score", summary["test_metrics"]["rule"]))
    lines.extend(
        metric_lines(
            "Logistic baseline: scikit-learn Pipeline + StandardScaler + class_weight=balanced",
            summary["test_metrics"]["logistic"],
        )
    )

    lines.extend(
        [
            "## Top Logistic Predictions on Test",
            "",
            "| Rank | Make | Model | Year | Component | As-of | Label | Days to Recall | Score | Campaigns |",
            "|---:|---|---|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary["top_logistic_predictions"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_family']} | {row['as_of_date']} | {row['label']} "
            f"| {row['days_to_first_recall']} | {row['score']} | {row['matched_campaign_numbers']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is still an MVP ranking baseline, not a production recall-probability model.",
            "- The task is a rare-event ranking problem, so AP and precision@K matter more than accuracy.",
            "- Training and batch scoring are now separate operational steps.",
            "- This separation is required before adding scheduled retraining, model promotion, or online serving.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
