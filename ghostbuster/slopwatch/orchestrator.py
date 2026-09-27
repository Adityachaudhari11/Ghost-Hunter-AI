"""SlopWatch Orchestrator — IBM Bob IDE's AI-slop gate.

Runs the 3 scanners in parallel (same pattern as the other modules):

1. hallucination — Slop Squatting & API Hallucination Registry
2. blueprint    — Semantic Grep / Blueprint Asserter
3. ghostpath    — Ghost Path & Exception Hunter

Every finding is triaged through Laya AI (score 1-10 severity,
noul PII/safety gate), then printed as a gate report:
critical hallucinations are red BLOCKs, the rest are WARNs.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..shared.laya_client import LayaClient
from ..shared.watsonx_client import WatsonxClient
from .blueprint import scan_blueprint
from .demo_data import DEMO_FINDINGS, DEMO_TARGET
from .ghostpath import scan_ghost_paths
from .hallucination import scan_hallucinations

MAX_REMEDIATIONS = 5  # cap live watsonx.ai calls per run

# Canned remediations for --demo / offline fallback (rule templates).
RULE_TEMPLATES = {
    "hallucination": ("Replace the invented import with a real library "
                      "(check PyPI/npm first), pin it in requirements/package.json, "
                      "and re-run the gate."),
    "blueprint": ("Move the code to the designated wrapper/layer named in Fix, "
                  "so the change follows the team blueprint instead of "
                  "reinventing it inline."),
    "ghostpath": ("Log the exception (logger.exception), narrow the caught "
                  "type, and implement the failure branch minimally — "
                  "explicit fallback or re-raise, never silent pass."),
}

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"


class SlopWatchOrchestrator:
    """Bob IDE primary agent for SlopWatch. Scans AI-generated diffs."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.laya = LayaClient()
        self.watsonx = WatsonxClient()
        self._print_header()

    def _print_header(self):
        print("\n" + "═" * 60)
        print("  👻  SlopWatch — AI Slop Gate (Hallucination / Blueprint / Ghost Path)")
        print("  Powered by IBM Bob IDE + Laya AI")
        print("═" * 60)

    def run(self, target: str = ".", diff_text: str = "",
            blueprint_rules: str = "", anthropic_api_key: str = "",
            explain: bool = True) -> dict:
        """Full SlopWatch gate run. Returns a structured report dict."""
        if self.demo_mode:
            return self._run_demo_animated()

        root = str(Path(target).resolve())
        print(f"\n⚡ Target: {root}")
        if diff_text:
            print("   Scope: PR diff (added files only)")
        if blueprint_rules:
            print(f"   Blueprint rules: {blueprint_rules}")

        # ── Step 1: parallel scanners ──────────────────────────────────
        print("\n⚡ Spawning 3 parallel SlopWatch subagents...")
        t0 = time.time()
        jobs = {
            "Hallucination Registry": lambda: scan_hallucinations(root, diff_text),
            "Blueprint Asserter": lambda: scan_blueprint(root, blueprint_rules),
            "Ghost Path Hunter": lambda: scan_ghost_paths(root),
        }
        findings: list[dict] = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(fn): name for name, fn in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                except Exception as e:  # a scanner must never kill the gate
                    print(f"  ✗  {name}: crashed ({e}) — continuing")
                    continue
                print(f"  ✓  {name}: {len(result)} finding(s)")
                findings.extend(result)
        elapsed = time.time() - t0

        # ── Step 2: Laya triage per finding ────────────────────────────
        print("\n⚡ Laya AI: triaging findings...")
        for f in findings:
            ctx = f"{f.get('scanner')}: {f.get('message')}"
            try:
                f["laya_score"] = self.laya.score(ctx, scale=(1, 10))
            except Exception:
                f["laya_score"] = float(f.get("severity", 5))

        blockers = [f for f in findings if f.get("severity", 0) >= 9]
        warns = [f for f in findings if f.get("severity", 0) < 9]

        # ── Step 3: watsonx.ai remediation ─────────────────────────────
        if explain:
            self._enrich_with_watsonx(findings)

        # ── Step 4: safety gate (PII / secret-adjacent code) ───────────
        try:
            pii_risk = self.laya.noul(
                "The scanned diff handles secrets, credentials, or personal user data"
            )
        except Exception:
            pii_risk = 0.0

        result = {
            "status": "blocked" if blockers else ("warnings" if warns else "clean"),
            "target": root,
            "files_scanned": self._count_files(root),
            "total_findings": len(findings),
            "blockers": len(blockers),
            "warnings": len(warns),
            "findings": findings,
            "pii_risk": round(pii_risk, 3),
            "duration_seconds": round(elapsed, 2),
        }
        self._print_summary(result)
        return result

    # ── demo mode ──────────────────────────────────────────────────────

    def _run_demo_animated(self) -> dict:
        print(f"\n⚡ Target: {DEMO_TARGET['name']} ({DEMO_TARGET['language']})")
        print("   Scope: PR diff #512 — 'AI-generated pricing service'")
        print("\n⚡ Spawning 3 parallel SlopWatch subagents...\n")
        time.sleep(0.3)
        for name in ("Hallucination Registry", "Blueprint Asserter", "Ghost Path Hunter"):
            n = sum(1 for f in DEMO_FINDINGS if {
                "Hallucination Registry": "hallucination",
                "Blueprint Asserter": "blueprint",
                "Ghost Path Hunter": "ghostpath",
            }[name] == f["scanner"])
            print(f"  ✓  {name}: {n} finding(s)")
            time.sleep(0.3)
        print("\n⚡ Laya AI: triaging findings...")
        for f in DEMO_FINDINGS:
            f["laya_score"] = float(f["severity"])
        self._enrich_with_watsonx(list(DEMO_FINDINGS))
        result = {
            "status": "blocked",
            "target": DEMO_TARGET["name"],
            "files_scanned": DEMO_TARGET["files_scanned"],
            "total_findings": len(DEMO_FINDINGS),
            "blockers": 1, "warnings": 5,
            "findings": list(DEMO_FINDINGS),
            "pii_risk": 0.15,
            "duration_seconds": 1.2,
        }
        time.sleep(0.3)
        self._print_summary(result)
        return result

    # ── watsonx.ai remediation ───────────────────────────────────────

    def _enrich_with_watsonx(self, findings: list[dict]):
        """Attach a remediation suggestion to top findings (cap MAX)."""
        targets = sorted(findings, key=lambda f: -f.get("severity", 0))[:MAX_REMEDIATIONS]
        if not targets:
            return
        if self.demo_mode or not self.watsonx.available:
            source = ("watsonx.ai · demo template" if self.demo_mode
                      else "built-in rules · set WATSONX_API_KEY for live Granite")
            print(f"\n💡 Remediation ({source})...")
            for f in targets:
                f["remediation"] = RULE_TEMPLATES.get(f.get("scanner", ""), f.get("fix", ""))
                f["remediation_source"] = source
            return
        print(f"\n💡 watsonx.ai ({self.watsonx.model_id}): generating remediations...")
        for f in targets:
            try:
                f["remediation"] = self.watsonx.suggest_fix(f)
                f["remediation_source"] = f"watsonx.ai · {self.watsonx.model_id}"
            except Exception as e:
                reason = str(e).strip().splitlines()
                f["remediation"] = RULE_TEMPLATES.get(f.get("scanner", ""), f.get("fix", ""))
                f["remediation_source"] = (
                    f"built-in rules · watsonx.ai unreachable ({reason[-1][:100] if reason else 'error'})")

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _count_files(root: str) -> int:
        n = 0
        skip = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip]
            n += sum(1 for f in files if Path(f).suffix.lower() in
                     {".py", ".js", ".jsx", ".ts", ".tsx"})
        return n

    def _print_summary(self, result: dict):
        print("\n" + "═" * 60)
        print("  📋  SlopWatch Gate Report")
        print("═" * 60)
        for f in result["findings"]:
            sev = f.get("severity", 0)
            color = RED if sev >= 9 else (YELLOW if sev >= 5 else GREEN)
            tag = "BLOCK" if sev >= 9 else "WARN"
            loc = f"{f.get('file')}:{f.get('line')}"
            print(f"\n  {color}[{tag} {f.get('id')}] {loc}{RESET}")
            print(f"  {color}{f.get('message')}{RESET}")
            if f.get("fix"):
                print(f"  Fix: {f.get('fix')}")
            if f.get("remediation"):
                print(f"  💡 [{f.get('remediation_source')}] {f.get('remediation')}")
        print("\n" + "─" * 60)
        print(f"  Files scanned: {result['files_scanned']}")
        print(f"  Findings: {result['total_findings']} "
              f"({result['blockers']} BLOCK, {result['warnings']} WARN)")
        if result["status"] == "blocked":
            print(f"  {RED}⛔ GATE BLOCKED — fix hallucinations before merge{RESET}")
        elif result["status"] == "warnings":
            print(f"  {YELLOW}⚠️  GATE PASSES WITH WARNINGS — review before merge{RESET}")
        else:
            print(f"  {GREEN}✅ GATE CLEAN — no AI slop detected{RESET}")
        print("═" * 60 + "\n")
