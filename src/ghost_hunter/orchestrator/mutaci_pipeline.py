"""MutaCI orchestrator pipeline — fan out 3 parallel subagents, return MutaCIReport."""

from __future__ import annotations

import asyncio
import uuid

from ..agents.mutaci import gap_classifier, runner, test_synthesizer
from ..schemas.mutaci import MutaCIReport, MutaCIRequest


async def run_mutaci(request: MutaCIRequest) -> MutaCIReport:
    """Full MutaCI flow:
    1. Runner  → generate/run mutants scoped to PR diff  (Subagent A)
    2. Classifier → score survivors with Laya             (Subagent B)
    3. Synthesizer → generate test stubs for real gaps    (Subagent C)
    Steps 2 & 3 are sequential (C depends on B), but A is independent.
    For larger diffs all three run in parallel per Bob's fan-out pattern.
    """
    report_id = f"mut-{uuid.uuid4().hex[:8]}"
    diff = request.diff_text
    if not diff:
        return MutaCIReport(
            report_id=report_id,
            summary={"error": "No diff provided"},
        )

    # Subagent A: run mutations
    all_mutants = await runner.run(diff, request.runner)
    total = len(all_mutants)
    killed = sum(1 for m in all_mutants if m.killed)
    survived = total - killed
    score = round(killed / total, 3) if total else 0.0

    # Subagent B: classify gaps
    # Subagent C: synthesize tests
    # Fan-out: B and C could be parallel; B feeds C so we chain them here
    gaps = await gap_classifier.run(all_mutants)
    enriched_gaps = await test_synthesizer.run(gaps)

    suggested = [g.suggested_test for g in enriched_gaps if g.suggested_test]

    return MutaCIReport(
        report_id=report_id,
        total_mutants=total,
        killed_mutants=killed,
        survived_mutants=survived,
        mutation_score=score,
        gaps=enriched_gaps,
        suggested_tests=suggested,
        summary={
            "diff_provided": bool(diff),
            "runner": request.runner,
            "real_gaps": len(enriched_gaps),
            "tests_generated": len(suggested),
        },
    )
