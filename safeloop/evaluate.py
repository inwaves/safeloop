"""Command line evaluation entry point."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from safeloop.harness import load_harness
from safeloop.models import create_model_client
from safeloop.runner import default_out_dir, run_suite
from safeloop.tasks import load_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a SafeLoop harness evaluation.")
    parser.add_argument("--suite", default="scope_smoke")
    parser.add_argument("--harness", default="scope_basic_v0")
    parser.add_argument("--model", required=True, help="provider:model, e.g. fake:safe")
    parser.add_argument("--k", type=int, default=1, help="Attempts per task")
    parser.add_argument("--max-seconds", type=float, help="Wall-clock seconds per attempt")
    parser.add_argument("--max-cost", type=float, help="API cost limit in USD per attempt")
    parser.add_argument("--out", help="Output directory")
    parser.add_argument("--overwrite", action="store_true", help="Replace output directory if it exists")
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")
    if args.max_seconds is not None and args.max_seconds < 0:
        raise SystemExit("--max-seconds must be >= 0")
    if args.max_cost is not None and args.max_cost < 0:
        raise SystemExit("--max-cost must be >= 0")

    harness = load_harness(args.harness)
    suite = load_suite(args.suite)
    model = create_model_client(args.model)

    out = Path(args.out) if args.out else default_out_dir(args.suite, harness.name, args.model)
    if out.exists() and args.overwrite:
        shutil.rmtree(out)

    summary = run_suite(
        suite=suite,
        suite_name=args.suite,
        harness=harness,
        model_name=args.model,
        model=model,
        out_dir=out,
        k=args.k,
        max_seconds=args.max_seconds,
        max_cost=args.max_cost,
    )

    print(f"out={out}")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
