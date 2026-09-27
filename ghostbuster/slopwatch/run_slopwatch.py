#!/usr/bin/env python3
"""SlopWatch CLI entry point."""

import argparse
import json
import os
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description="SlopWatch — AI slop gate (hallucination / blueprint / ghost path)")
    parser.add_argument("--target", default=".",
                        help="Local path OR GitHub URL (https://github.com/owner/repo[.git]) to scan")
    parser.add_argument("--branch", default="", help="Branch to checkout when --target is a GitHub URL")
    parser.add_argument("--keep-clone", action="store_true",
                        help="Keep the temp clone (default: deleted after the scan)")
    parser.add_argument("--diff", default="", help="Path to a unified diff file (scan only touched files)")
    parser.add_argument("--blueprint", default="", dest="blueprint_rules",
                        help="Path to custom blueprint rules JSON")
    parser.add_argument("--demo", action="store_true", help="Run with pre-recorded demo data")
    parser.add_argument("--explain", dest="explain", action=argparse.BooleanOptionalAction,
                        default=True, help="Attach watsonx.ai remediation suggestions (default: on)")
    parser.add_argument("--output-json", default="", help="Write full report JSON to this file")
    args = parser.parse_args()

    diff_text = ""
    if args.diff:
        with open(args.diff, encoding="utf-8", errors="ignore") as f:
            diff_text = f.read()

    from ghostbuster.slopwatch.github import clone_repo, is_github_url
    from ghostbuster.slopwatch.orchestrator import SlopWatchOrchestrator

    target = args.target
    tmp_root = ""
    if is_github_url(target) and not args.demo:
        try:
            target = clone_repo(target, branch=args.branch)
            tmp_root = os.path.dirname(target.rstrip(os.sep))  # <tmp> holding <tmp>/repo
        except RuntimeError as e:
            print(f"\n⛔ {e}")
            sys.exit(2)

    try:
        orchestrator = SlopWatchOrchestrator(demo_mode=args.demo)
        report = orchestrator.run(
            target=target,
            diff_text=diff_text,
            blueprint_rules=args.blueprint_rules,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            explain=args.explain,
        )
    finally:
        if tmp_root and not args.keep_clone:
            shutil.rmtree(tmp_root, ignore_errors=True)

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output_json}")

    sys.exit(1 if report.get("status") == "blocked" else 0)


if __name__ == "__main__":
    main()
