from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from baseline_backfill_common import (  # noqa: E402
    DOCS_DIR,
    PROCESSED_BACKFILL_DIR,
    REPORTS_DIR,
    display_path,
    latest_run_dir,
    read_json,
    resolve_project_path,
    write_json,
)


PROMOTION_STATUS_APPROVED = "approved"
PROMOTION_STATUS_REJECTED = "rejected"


def metric_at_k(metrics: dict[str, Any], k: int, name: str) -> float:
    for item in metrics.get("precision_recall_at_k", []):
        if int(item["k"]) == k:
            return float(item[name])
    return 0.0


def add_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    passed: bool,
    actual: Any,
    expected: Any,
    blocking: bool = True,
) -> None:
    checks.append(
        {
            "name": name,
            "passed": passed,
            "blocking": blocking,
            "actual": actual,
            "expected": expected,
        }
    )


def evaluate_promotion(
    *,
    summary: dict[str, Any],
    processed_run_dir: Path,
    min_test_positives: int,
    min_ap_delta: float,
    max_brier_regression: float,
    precision_k: int,
    require_precision_at_k: bool,
) -> dict[str, Any]:
    run_id = processed_run_dir.name
    rule_metrics = summary["test_metrics"]["rule"]
    logistic_metrics = summary["test_metrics"]["logistic"]
    test_split = summary["split"]["test"]

    model_artifact_path = resolve_project_path(summary.get("model_artifact"))
    predictions_path = resolve_project_path(summary.get("predictions_csv"))

    rule_ap = float(rule_metrics["average_precision"])
    logistic_ap = float(logistic_metrics["average_precision"])
    rule_brier = float(rule_metrics["brier_score"])
    logistic_brier = float(logistic_metrics["brier_score"])
    rule_precision_at_k = metric_at_k(rule_metrics, precision_k, "precision")
    logistic_precision_at_k = metric_at_k(logistic_metrics, precision_k, "precision")
    rule_hits_at_k = metric_at_k(rule_metrics, precision_k, "hits")
    logistic_hits_at_k = metric_at_k(logistic_metrics, precision_k, "hits")

    checks: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    add_check(
        checks,
        name="model_artifact_exists",
        passed=bool(model_artifact_path and model_artifact_path.exists()),
        actual=display_path(model_artifact_path) if model_artifact_path else None,
        expected="existing model artifact",
    )
    add_check(
        checks,
        name="predictions_csv_exists",
        passed=bool(predictions_path and predictions_path.exists()),
        actual=display_path(predictions_path) if predictions_path else None,
        expected="existing prediction CSV",
    )
    add_check(
        checks,
        name="test_positive_count",
        passed=int(test_split["positive_count"]) >= min_test_positives,
        actual=int(test_split["positive_count"]),
        expected=f">= {min_test_positives}",
    )
    add_check(
        checks,
        name="logistic_ap_not_worse_than_rule",
        passed=(logistic_ap - rule_ap) >= min_ap_delta,
        actual=round(logistic_ap - rule_ap, 8),
        expected=f">= {min_ap_delta}",
    )
    add_check(
        checks,
        name="logistic_brier_not_worse_than_rule",
        passed=(logistic_brier - rule_brier) <= max_brier_regression,
        actual=round(logistic_brier - rule_brier, 8),
        expected=f"<= {max_brier_regression}",
    )

    precision_check_passed = logistic_precision_at_k >= rule_precision_at_k
    precision_check = {
        "name": f"logistic_precision_at_{precision_k}_not_worse_than_rule",
        "passed": precision_check_passed,
        "blocking": require_precision_at_k,
        "actual": logistic_precision_at_k,
        "expected": f">= {rule_precision_at_k}",
        "rule_hits": rule_hits_at_k,
        "logistic_hits": logistic_hits_at_k,
    }
    if require_precision_at_k:
        checks.append(precision_check)
    elif not precision_check_passed:
        warnings.append(precision_check)

    blocking_failures = [check for check in checks if check["blocking"] and not check["passed"]]
    status = PROMOTION_STATUS_REJECTED if blocking_failures else PROMOTION_STATUS_APPROVED

    return {
        "source_run_id": run_id,
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "promotion_status": status,
        "approved": status == PROMOTION_STATUS_APPROVED,
        "gate_config": {
            "min_test_positives": min_test_positives,
            "min_ap_delta": min_ap_delta,
            "max_brier_regression": max_brier_regression,
            "precision_k": precision_k,
            "require_precision_at_k": require_precision_at_k,
        },
        "metrics": {
            "rule_average_precision": rule_ap,
            "logistic_average_precision": logistic_ap,
            "average_precision_delta": round(logistic_ap - rule_ap, 8),
            "rule_brier_score": rule_brier,
            "logistic_brier_score": logistic_brier,
            "brier_score_delta": round(logistic_brier - rule_brier, 8),
            f"rule_precision_at_{precision_k}": rule_precision_at_k,
            f"logistic_precision_at_{precision_k}": logistic_precision_at_k,
            f"rule_hits_at_{precision_k}": rule_hits_at_k,
            f"logistic_hits_at_{precision_k}": logistic_hits_at_k,
            "test_row_count": int(test_split["row_count"]),
            "test_positive_count": int(test_split["positive_count"]),
        },
        "artifacts": {
            "model_artifact": display_path(model_artifact_path) if model_artifact_path else "",
            "predictions_csv": display_path(predictions_path) if predictions_path else "",
        },
        "checks": checks,
        "warnings": warnings,
        "blocking_failures": blocking_failures,
    }


def write_markdown_report(decision: dict[str, Any], report_path: Path) -> None:
    metrics = decision["metrics"]
    lines = [
        "# Model Promotion Gate Results",
        "",
        f"- Source run ID: `{decision['source_run_id']}`",
        f"- Evaluated at UTC: `{decision['evaluated_at_utc']}`",
        f"- Promotion status: `{decision['promotion_status']}`",
        "",
        "## Gate config",
        "",
        "| Setting | Value |",
        "|---|---:|",
    ]
    for key, value in decision["gate_config"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    for key, value in metrics.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Blocking checks",
            "",
            "| Check | Passed | Actual | Expected |",
            "|---|---:|---:|---:|",
        ]
    )
    for check in decision["checks"]:
        lines.append(
            f"| {check['name']} | {check['passed']} | {check['actual']} | {check['expected']} |"
        )

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if decision["warnings"]:
        lines.extend(
            [
                "| Warning | Passed | Actual | Expected | Rule hits | Logistic hits |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for warning in decision["warnings"]:
            lines.append(
                f"| {warning['name']} | {warning['passed']} | {warning['actual']} "
                f"| {warning['expected']} | {warning.get('rule_hits', '')} "
                f"| {warning.get('logistic_hits', '')} |"
            )
    else:
        lines.append("No warnings.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Approved means the model is allowed to produce latest-week serving scores.",
            "- Rejected means the DAG should stop before `score_latest` publishes model scores.",
            "- Current default gate blocks on AP/Brier/test-size checks and warns on top-K precision.",
            "- Tighten `--require-precision-at-k` after the ranking model improves.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate whether a trained model may be promoted.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--min-test-positives", type=int, default=10)
    parser.add_argument("--min-ap-delta", type=float, default=0.0)
    parser.add_argument("--max-brier-regression", type=float, default=0.0)
    parser.add_argument("--precision-k", type=int, default=25)
    parser.add_argument(
        "--require-precision-at-k",
        action="store_true",
        help="Make precision@K comparison a blocking promotion check.",
    )
    parser.add_argument(
        "--allow-rejected-exit-zero",
        action="store_true",
        help="Write a rejected decision but exit 0. Do not use for publishing DAGs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    summary_path = processed_run_dir / "baseline_model_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"{display_path(summary_path)} is missing. Run score_batch_backfill.py first."
        )

    decision = evaluate_promotion(
        summary=read_json(summary_path),
        processed_run_dir=processed_run_dir,
        min_test_positives=args.min_test_positives,
        min_ap_delta=args.min_ap_delta,
        max_brier_regression=args.max_brier_regression,
        precision_k=args.precision_k,
        require_precision_at_k=args.require_precision_at_k,
    )

    decision_path = processed_run_dir / "model_promotion_decision.json"
    write_json(decision_path, decision)

    report_path = REPORTS_DIR / "model_promotion_gate_latest.md"
    write_markdown_report(decision, report_path)

    docs_result_path = DOCS_DIR / "MODEL_PROMOTION_GATE_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Promotion status: {decision['promotion_status']}")
    print(f"AP delta:         {decision['metrics']['average_precision_delta']}")
    print(f"Brier delta:      {decision['metrics']['brier_score_delta']}")
    print(f"Warnings:         {len(decision['warnings'])}")
    print(f"Wrote:            {display_path(decision_path)}")
    print(f"Wrote:            {display_path(report_path)}")

    if decision["approved"] or args.allow_rejected_exit_zero:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
