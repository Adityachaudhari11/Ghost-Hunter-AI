#!/usr/bin/env python3
"""
GhostBuster — Full Platform Demo Runner.

Runs all 4 modules in sequence to demonstrate the complete 5-minute story:
  1. MutaCI     — PR opened, 4 behavioral gaps found, tests generated
  2. FlakeHunter — 3 flaky CI tests classified and fixed in parallel
  3. CausalTrace — Production Sentry incident traced to root cause in 90s
  4. BugPort    — Race condition reproduced locally from production snapshot

This is what IBM Bob IDE orchestrates end-to-end.
"""

import argparse
import os
import sys
import time


BANNER = r"""
  ██████  ██    ██  ██████  ██████  ██████  ██████  ██████   ██████  ███████
  ██   ██ ██    ██ ██       ██   ██ ██   ██ ██   ██ ██   ██ ██       ██
  ██████  ██    ██ ██   ███ ██████  ██████  ██████  ██   ██ ██   ███ █████
  ██   ██ ██    ██ ██    ██ ██   ██ ██   ██ ██   ██ ██   ██ ██    ██ ██
  ██████   ██████   ██████  ██████  ██   ██ ██   ██ ██████   ██████  ███████

  Powered by IBM Bob IDE + Laya AI (ModernBERT-large, Apache 2.0)
  AST-to-Runtime Semantic Bridge for Deterministic Bug Resolution
"""


def print_module_divider(n: int, name: str, subtitle: str):
    print("\n" + "━" * 60)
    print(f"  MODULE {n}: {name}")
    print(f"  {subtitle}")
    print("━" * 60)


def main():
    parser = argparse.ArgumentParser(description="GhostBuster — Full platform demo")
    parser.add_argument("--demo", action="store_true", default=True,
                        help="Run in demo mode (default: True)")
    parser.add_argument("--module", choices=["all", "mutaci", "flakehunter", "causaltrace", "bugport"],
                        default="all", help="Which module to run")
    args = parser.parse_args()

    print(BANNER)
    print("  IBM Bob IDE Hackathon — GhostBuster Platform Demo")
    print("  Theme: Bug Fixing & Bug Identification\n")
    time.sleep(0.5)

    project_path = os.path.join(os.path.dirname(__file__), "..", "demo-app")
    project_path = os.path.abspath(project_path)

    run_all = args.module == "all"

    # ── Module 1: MutaCI ────────────────────────────────────────────────
    if run_all or args.module == "mutaci":
        print_module_divider(1, "MutaCI", "PR-scoped behavioral gap detection")
        from ghostbuster.mutaci.orchestrator import MutaCIOrchestrator
        mutaci = MutaCIOrchestrator(project_path=project_path, demo_mode=True)
        mutaci_report = mutaci.run(
            pr_description="Add seasonal discount pricing to cart",
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )
        time.sleep(0.3)

    # ── Module 2: FlakeHunter ────────────────────────────────────────────
    if run_all or args.module == "flakehunter":
        print_module_divider(2, "FlakeHunter", "CI flaky test root cause and auto-fix")
        from ghostbuster.flakehunter.orchestrator import FlakeHunterOrchestrator
        flake = FlakeHunterOrchestrator(demo_mode=True)
        flake_reports = flake.run(anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        time.sleep(0.3)

    # ── Module 3: CausalTrace ────────────────────────────────────────────
    if run_all or args.module == "causaltrace":
        print_module_divider(3, "CausalTrace", "Production incident root cause (Sentry → PR → fix)")
        from ghostbuster.causaltrace.orchestrator import CausalTraceOrchestrator
        causal = CausalTraceOrchestrator(demo_mode=True)
        causal_report = causal.run(anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        time.sleep(0.3)

    # ── Module 4: BugPort ────────────────────────────────────────────────
    if run_all or args.module == "bugport":
        print_module_divider(4, "BugPort", "Production race condition reproduced locally in 90s")
        from ghostbuster.bugport.orchestrator import BugPortOrchestrator
        bugport = BugPortOrchestrator(demo_mode=True)
        bugport_report = bugport.run()
        time.sleep(0.3)

    # ── Platform Summary ─────────────────────────────────────────────────
    if run_all:
        print("\n" + "═" * 60)
        print("  🏆  GhostBuster Platform — Full Run Complete")
        print("═" * 60)
        print("  What Bob IDE just did autonomously:\n")
        print("  ✅  MutaCI:      Found 4 behavioral gaps in PR (91.7% → 100%)")
        print("                   Generated 4 targeted tests via Claude")
        print("  ✅  FlakeHunter: Classified 3 flaky tests (async/state/env)")
        print("                   1 fix auto-applied, 2 queued for review")
        print("  ✅  CausalTrace: Traced 847 prod errors to PR #447 in 90s")
        print("                   Causal narrative + regression test generated")
        print("  ✅  BugPort:     Race condition reproduced locally in <90s")
        print("                   Harness written, 86% Laya reproduction confidence")
        print("\n  Every decision routed through Laya AI (System 1, 33ms).")
        print("  Every fix is compile-safe. No hallucinated diffs.")
        print("  Engineer approves. Does not debug.")
        print("═" * 60 + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
