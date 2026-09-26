#!/usr/bin/env python3
"""
MutaCI CLI entry point.
Usage:
    python -m ghostbuster.mutaci.run_mutaci [--demo] [--project PATH] [--pr-desc TEXT]

--demo: Use pre-recorded mutation results (no Stryker install needed)
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="MutaCI — PR-scoped mutation testing by GhostBuster"
    )
    parser.add_argument(
        "--project",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "demo-app"),
        help="Path to the TypeScript project (default: demo-app/)",
    )
    parser.add_argument(
        "--pr-desc",
        default="Add seasonal discount pricing to cart",
        help="PR description / title (used for context-aware test generation)",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch to diff against (default: main)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode (simulated results, no Stryker needed)",
    )
    parser.add_argument(
        "--output-json",
        help="Write full report JSON to this file path",
    )
    args = parser.parse_args()

    # Resolve project path
    project_path = os.path.abspath(args.project)
    if not os.path.isdir(project_path):
        print(f"Error: project path not found: {project_path}")
        sys.exit(1)

    from ghostbuster.mutaci.orchestrator import MutaCIOrchestrator

    orchestrator = MutaCIOrchestrator(
        project_path=project_path,
        demo_mode=args.demo,
    )

    report = orchestrator.run(
        pr_description=args.pr_desc,
        base_branch=args.base_branch,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output_json}")

    sys.exit(0 if report.get("status") in ("clean", "no_changes") else 1)


if __name__ == "__main__":
    main()
