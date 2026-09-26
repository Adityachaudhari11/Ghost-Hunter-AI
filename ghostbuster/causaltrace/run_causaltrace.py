#!/usr/bin/env python3
"""
CausalTrace CLI entry point.
Usage:
    python -m ghostbuster.causaltrace.run_causaltrace [--demo] [--sentry-json PATH]
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="CausalTrace — Incident root cause agent by GhostBuster"
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run with pre-recorded incident data")
    parser.add_argument("--sentry-json", help="Path to Sentry event JSON file")
    parser.add_argument("--output-json", help="Write full report JSON to this file")
    args = parser.parse_args()

    sentry_event = None
    if args.sentry_json and os.path.exists(args.sentry_json):
        with open(args.sentry_json) as f:
            sentry_event = json.load(f)

    from ghostbuster.causaltrace.orchestrator import CausalTraceOrchestrator

    orchestrator = CausalTraceOrchestrator(demo_mode=args.demo or not sentry_event)
    report = orchestrator.run(
        sentry_event=sentry_event,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output_json}")

    sys.exit(0)


if __name__ == "__main__":
    main()
