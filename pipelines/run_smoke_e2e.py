from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "ci_fixture"


def run_step(command: list[str]) -> None:
    printable = " ".join(command)
    print(f"\n$ {printable}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic offline sample E2E pipeline for clean-clone/CI checks."
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python = sys.executable
    run_step([python, "pipelines/prepare_smoke_fixture.py", "--run-id", args.run_id])
    run_step([python, "pipelines/normalize_sample.py", "--run-id", args.run_id])
    run_step(
        [
            python,
            "pipelines/build_features_sample.py",
            "--run-id",
            args.run_id,
            "--top-k",
            str(args.top_k),
        ]
    )
    run_step([python, "pipelines/build_training_dataset_sample.py", "--run-id", args.run_id])
    run_step(
        [
            python,
            "pipelines/train_baseline_sample.py",
            "--run-id",
            args.run_id,
            "--max-iter",
            str(args.max_iter),
        ]
    )
    print("\nSmoke E2E complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

