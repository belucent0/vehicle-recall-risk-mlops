from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility wrapper. Runs split train_model_backfill.py and "
            "score_batch_backfill.py in sequence."
        )
    )
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument("--negative-ratio", type=int, default=20)
    parser.add_argument("--max-train-rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    train_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "pipelines" / "train_model_backfill.py"),
        "--epochs",
        str(args.epochs),
        "--max-iter",
        str(args.max_iter),
        "--negative-ratio",
        str(args.negative_ratio),
        "--max-train-rows",
        str(args.max_train_rows),
        "--seed",
        str(args.seed),
    ]
    score_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "pipelines" / "score_batch_backfill.py"),
    ]

    if args.run_id:
        train_cmd.extend(["--run-id", args.run_id])
        score_cmd.extend(["--run-id", args.run_id])

    subprocess.run(train_cmd, cwd=PROJECT_ROOT, check=True)
    subprocess.run(score_cmd, cwd=PROJECT_ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
