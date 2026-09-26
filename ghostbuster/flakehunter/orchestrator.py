"""
FlakeHunter Orchestrator — IBM Bob IDE's CI reliability agent.

Flow:
1. Accept 1+ CI failure logs (or demo staged logs)
2. [Laya] Classify root cause per test (async / state / ordering / environment / resource)
3. [Bob parallel] Spawn 3 subagents in parallel: Pattern + Code + History
4. Generate a targeted fix per root cause class
5. Validate fix description plausibility with Laya noul
6. Output fix report + patched test files
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Optional

from ..shared.laya_client import LayaClient
from .classifier import FlakeClassification, classify_flake
from .fix_generator import FlakeFix, generate_fix

# Demo staged CI failure logs — 3 different root cause categories
DEMO_LOGS = {
    "tests/auth.test.ts::login_flow": """
FAIL tests/auth.test.ts
  ● login_flow › should redirect after successful login

    Timeout - Async callback was not invoked within the 5000ms timeout.

      45 | it('should redirect after successful login', (done) => {
      46 |   loginUser('test@example.com', 'password123');
    > 47 |   setTimeout(done, 3000);
         |   ^
      48 | });

    at Timeout._onTimeout (node_modules/jest-jasmine2/build/jestAdapterInit.js:237:10)
""",
    "tests/cart.test.ts::item_count": """
FAIL tests/cart.test.ts
  ● item_count › should return correct count after add

    expect(received).toBe(expected)
    Expected: 1
    Received: 4

      12 | it('should return correct count after add', () => {
    > 13 |   expect(cart.itemCount()).toBe(1);
         |   ^

    The global cart was mutated by a beforeAll hook in a different describe block.
    Run tests in isolation to reproduce.
""",
    "tests/api.test.ts::health_check": """
FAIL tests/api.test.ts
  ● health_check › should return 200

    connect ECONNREFUSED 127.0.0.1:3001

      8 | it('should return 200', async () => {
    > 9 |   const res = await fetch('http://localhost:3001/health');
         |   ^
     10 |   expect(res.status).toBe(200);
     11 | });

    Port 3001 is already in use or the server is not running.
    This test passes when run alone but fails in the full suite.
""",
}

# Minimal synthetic test content for demo fix generation
DEMO_TEST_CONTENT: dict[str, str] = {
    "tests/auth.test.ts::login_flow": """import { loginUser } from '../src/auth';

describe('login_flow', () => {
  it('should redirect after successful login', (done) => {
    loginUser('test@example.com', 'password123');
    setTimeout(done, 3000);
  });
});
""",
    "tests/cart.test.ts::item_count": """import { Cart } from '../src/cart';

const cart = new Cart();

beforeAll(() => {
  cart.addItem({ id: '1', price: 10 });
  cart.addItem({ id: '2', price: 20 });
  cart.addItem({ id: '3', price: 30 });
});

describe('item_count', () => {
  it('should return correct count after add', () => {
    cart.addItem({ id: '4', price: 40 });
    expect(cart.itemCount()).toBe(1);
  });
});
""",
    "tests/api.test.ts::health_check": """describe('health_check', () => {
  it('should return 200', async () => {
    const res = await fetch('http://localhost:3001/health');
    expect(res.status).toBe(200);
  });
});
""",
}


@dataclass
class FlakeReport:
    test_id: str
    classification: FlakeClassification
    fix: FlakeFix
    laya_fix_valid: float   # Laya noul: probability the fix is semantically correct
    auto_apply_safe: bool


class FlakeHunterOrchestrator:
    """
    Bob IDE primary agent for FlakeHunter.
    Classifies flaky tests and generates targeted fixes in parallel.
    """

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.laya = LayaClient()
        self._print_header()

    def _print_header(self):
        print("\n" + "═" * 60)
        print("  🔥  FlakeHunter — CI Reliability Agent")
        print("  Powered by IBM Bob IDE + Laya AI")
        print("═" * 60)

    def run(
        self,
        ci_logs: Optional[dict[str, str]] = None,
        anthropic_api_key: str = "",
    ) -> list[dict]:
        """
        Run FlakeHunter on the given CI logs.
        ci_logs: {test_id: log_text} — if None in demo mode, uses staged demo logs.
        """
        if self.demo_mode or not ci_logs:
            logs = DEMO_LOGS
            test_contents = DEMO_TEST_CONTENT
        else:
            logs = ci_logs
            test_contents = {}

        import anthropic as _anthropic
        client = None
        if anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"):
            key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
            client = _anthropic.Anthropic(api_key=key)

        print(f"\n⚡ Analyzing {len(logs)} flaky test(s) with parallel Bob subagents...\n")

        reports = []
        # Bob parallel subagents — one per flaky test
        with ThreadPoolExecutor(max_workers=min(len(logs), 4)) as pool:
            futures = {
                pool.submit(
                    self._analyze_one,
                    test_id,
                    log,
                    test_contents.get(test_id, ""),
                    client,
                ): test_id
                for test_id, log in logs.items()
            }
            for future in as_completed(futures):
                test_id = futures[future]
                try:
                    report = future.result()
                    reports.append(report)
                    self._print_result(report)
                except Exception as e:
                    print(f"  ⚠️  Error analyzing {test_id}: {e}")

        self._print_summary(reports)
        return [self._report_to_dict(r) for r in reports]

    def _analyze_one(
        self,
        test_id: str,
        log: str,
        test_content: str,
        client,
    ) -> FlakeReport:
        """Bob subagent: classify one flaky test and generate its fix."""
        # Pattern Agent (Laya): classify root cause
        classification = classify_flake(log, self.laya)

        # Code Agent: generate fix (Claude or demo)
        fix = generate_fix(
            classification,
            test_content or log[:500],
            test_id.split("::")[0],
            client=client,
        )

        # Laya safety gate: does the fix make semantic sense?
        fix_valid = self.laya.noul(
            f"The fix for a '{classification.category}' flaky test changes "
            f"the test to eliminate timing/state/environment dependency"
        )
        auto_apply_safe = fix_valid > 0.6 and classification.confidence > 0.5

        return FlakeReport(
            test_id=test_id,
            classification=classification,
            fix=fix,
            laya_fix_valid=fix_valid,
            auto_apply_safe=auto_apply_safe,
        )

    def _print_result(self, r: FlakeReport):
        cat_icon = {
            "async": "⏱️",
            "state": "🗂️",
            "ordering": "📋",
            "environment": "🌐",
            "resource": "💾",
        }.get(r.classification.category, "🔍")
        safe = "✅ auto-apply" if r.auto_apply_safe else "⚠️  review"
        print(f"  {cat_icon} [{r.classification.category.upper()}] {r.test_id}")
        print(f"     Confidence: {r.classification.confidence:.0%} | Fix validity: {r.laya_fix_valid:.0%} | {safe}")
        print(f"     Reasoning: {r.classification.reasoning.splitlines()[0]}")
        print(f"     Fix: {r.fix.description}")
        if r.fix.diff_lines:
            for line in r.fix.diff_lines[:6]:
                print(f"       {line}")
        print()

    def _print_summary(self, reports: list[FlakeReport]):
        auto = sum(1 for r in reports if r.auto_apply_safe)
        print("═" * 60)
        print("  📋  FlakeHunter Summary")
        print("═" * 60)
        print(f"  Flaky tests analyzed: {len(reports)}")
        print(f"  Auto-apply safe:      {auto}/{len(reports)}")
        cats = {}
        for r in reports:
            cats[r.classification.category] = cats.get(r.classification.category, 0) + 1
        for cat, count in cats.items():
            print(f"    {cat}: {count}")
        print("═" * 60 + "\n")

    def _report_to_dict(self, r: FlakeReport) -> dict:
        return {
            "test_id": r.test_id,
            "category": r.classification.category,
            "confidence": r.classification.confidence,
            "reasoning": r.classification.reasoning,
            "fix_template": r.classification.fix_template,
            "fix_description": r.fix.description,
            "patched_test": r.fix.patched_test,
            "laya_fix_valid": r.laya_fix_valid,
            "auto_apply_safe": r.auto_apply_safe,
        }
