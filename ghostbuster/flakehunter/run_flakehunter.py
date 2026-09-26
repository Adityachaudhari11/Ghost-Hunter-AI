#!/usr/bin/env python3
"""
FlakeHunter CLI entry point.
Usage:
    python -m ghostbuster.flakehunter.run_flakehunter [--demo] [--log-file PATH]
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="FlakeHunter — CI reliability agent by GhostBuster"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with staged flaky test logs",
    )
    parser.add_argument(
        "--log-file",
        help="Path to CI log file (JSON: {test_id: log_text})",
    )
    parser.add_argument(
        "--output-json",
        help="Write full report JSON to this file path",
    )
    args = parser.parse_args()

    ci_logs = None
    if args.log_file and os.path.exists(args.log_file):
        with open(args.log_file) as f:
            ci_logs = json.load(f)

    from ghostbuster.flakehunter.orchestrator import FlakeHunterOrchestrator

    orchestrator = FlakeHunterOrchestrator(demo_mode=args.demo or not ci_logs)
    reports = orchestrator.run(
        ci_logs=ci_logs,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(reports, f, indent=2)
        print(f"\nReport written to: {args.output_json}")

    sys.exit(0)


if __name__ == "__main__":
    main()
