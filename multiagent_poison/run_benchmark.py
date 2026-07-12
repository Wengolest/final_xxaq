#!/usr/bin/env python3
"""CLI entry point for MAS Safety Benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Load .env before imports that need API keys
try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

from mas_safety.evaluator.metrics import format_results_table
from mas_safety.runner import BenchmarkRunner
from mas_safety.types import AttackCategory, OrchestratorType


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MAS Safety Benchmark — evaluate multi-agent systems against "
        "hijacking, metadata poisoning, and RCE attacks (arXiv:2503.12188v2)",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "dry", "hijack-only", "baselines"],
        default="dry",
        help="full=live LLM trials, dry=offline fixture validation, "
        "hijack-only=MAS hijacking scenarios, baselines=IPI/direct-ask/benign",
    )
    parser.add_argument("--trials", type=int, default=3, help="Trials per scenario")
    parser.add_argument(
        "--orchestrator",
        choices=["central", "central_ledger", "round_robin"],
        default="central",
    )
    parser.add_argument("--simple", action="store_true", help="Use 2-agent setup instead of full MAS")
    parser.add_argument("--work-dir", default="benchmark_workspace")
    parser.add_argument("--results-dir", default="benchmark_results")
    args = parser.parse_args()

    orch_map = {
        "central": OrchestratorType.CENTRAL,
        "central_ledger": OrchestratorType.CENTRAL_LEDGER,
        "round_robin": OrchestratorType.ROUND_ROBIN,
    }

    runner = BenchmarkRunner(
        work_dir=args.work_dir,
        results_dir=args.results_dir,
        orchestrator_type=orch_map[args.orchestrator],
        use_full_mas=not args.simple,
        trials_per_scenario=args.trials,
    )

    categories = None
    if args.mode == "hijack-only":
        categories = [AttackCategory.MAS_HIJACKING]
    elif args.mode == "baselines":
        categories = [
            AttackCategory.INDIRECT_PROMPT_INJECTION,
            AttackCategory.DIRECT_ASK,
            AttackCategory.BENIGN,
            AttackCategory.PROMPT_INFECTION,
        ]

    print("=" * 60)
    print("MAS Safety Benchmark")
    print("Reference: arXiv:2503.12188v2 (MAS Hijacking / Control-Flow Attacks)")
    print("=" * 60)

    if args.mode == "dry":
        print("\n[DRY RUN] Validating attack fixtures & trace analyzer (no LLM calls)\n")
        results = runner.run_dry()
    else:
        print(f"\n[LIVE] Running {args.trials} trials per scenario...\n")
        results = runner.run(categories=categories)

    print(format_results_table(results))
    print(f"\nResults saved to: {Path(args.results_dir).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
