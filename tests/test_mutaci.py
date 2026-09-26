"""Tests for MutaCI module — mutation ingester + gap classifier + test synthesizer."""

from __future__ import annotations

import asyncio

from src.ghost_hunter.ingesters.mutation import generate_mutants_for_diff
from src.ghost_hunter.orchestrator.mutaci_pipeline import run_mutaci
from src.ghost_hunter.schemas.mutaci import MutaCIRequest


_DIFF = """\
--- a/payment/checkout.py
+++ b/payment/checkout.py
@@ -1,0 +1,4 @@
+def charge_payment(user, cart):
+    if amount > 0:
+        return process_charge(user.paymentMethod, amount)
+    return False
"""


def test_mutants_generated_for_diff():
    mutants = generate_mutants_for_diff(_DIFF, runner="stub")
    assert len(mutants) > 0
    for m in mutants:
        assert m.file == "payment/checkout.py"
        assert m.operator in ("AOR", "ROR", "LCR", "UOI", "SBR")


def test_survived_mutants_exist():
    mutants = generate_mutants_for_diff(_DIFF, runner="stub")
    survived = [m for m in mutants if not m.killed]
    assert isinstance(survived, list)


def test_mutaci_pipeline_returns_report():
    req = MutaCIRequest(diff_text=_DIFF, runner="stub")
    report = asyncio.run(run_mutaci(req))
    assert report.report_id.startswith("mut-")
    assert report.total_mutants >= 0
    assert 0.0 <= report.mutation_score <= 1.0
    assert isinstance(report.gaps, list)
    assert isinstance(report.suggested_tests, list)


def test_mutaci_empty_diff():
    req = MutaCIRequest(diff_text="", runner="stub")
    report = asyncio.run(run_mutaci(req))
    assert report.total_mutants == 0
    assert report.mutation_score == 0.0
