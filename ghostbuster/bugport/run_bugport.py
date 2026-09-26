#!/usr/bin/env python3
"""BugPort CLI entry point."""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="BugPort — Production reproduction agent")
    parser.add_argument("--demo", action="store_true", help="Run with demo race condition snapshot")
    parser.add_argument("--snapshot-json", help="Path to bug snapshot JSON file")
    parser.add_argument("--output-json", help="Write full report JSON to this file")
    args = parser.parse_args()

    from ghostbuster.bugport.orchestrator import BugPortOrchestrator
    orchestrator = BugPortOrchestrator(demo_mode=args.demo or not args.snapshot_json)
    report = orchestrator.run()

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output_json}")
    sys.exit(0)


if __name__ == "__main__":
    main()
