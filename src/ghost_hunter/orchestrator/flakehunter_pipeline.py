"""FlakeHunter orchestrator pipeline — 3 parallel subagents + Laya routing + fix."""

from __future__ import annotations

import asyncio
import uuid

from ..agents.flakehunter import (
    code_agent,
    fix_generator,
    ordering_agent,
    pattern_agent,
)
from ..laya.client import laya
from ..schemas.flakehunter import FlakeRootCause, FlakeReport, CIRunLog


async def run_flakehunter(
    test_id: str,
    logs: list[CIRunLog],
    test_source: str = "",
) -> FlakeReport:
    """Full FlakeHunter flow:
    1. Three agents run in parallel (fan-out):
       PatternAgent  — analyse CI log patterns
       CodeAgent     — inspect test source
       OrderingAgent — correlate predecessor failures
    2. Laya Choice: classify root cause from merged signals
    3. FixGenerator: deterministic fix for the classified root cause
    """
    report_id = f"flake-{uuid.uuid4().hex[:8]}"

    # Fan-out: all 3 subagents run simultaneously (Bob parallel tasks)
    pat_task = pattern_agent.run(logs)
    code_task = code_agent.run(test_source, test_id) if test_source else _noop_code()
    ord_task = ordering_agent.run(logs)
    pat_sig, code_sig, ord_sig = await asyncio.gather(pat_task, code_task, ord_task)

    # Build merged context for Laya classification
    context = {
        "test_id": test_id,
        "timing_hits": pat_sig.timing_hits,
        "state_hits": pat_sig.state_hits,
        "port_hits": pat_sig.port_hits,
        "patterns": pat_sig.raw_patterns[:3],
        "missing_awaits": bool(code_sig.missing_awaits),
        "hardcoded_timeouts": bool(code_sig.hardcoded_timeouts),
        "shared_mutable_state": bool(code_sig.shared_mutable_state),
        "predecessor_suspects": ord_sig.suspects[:2],
    }
    laya_result = await laya.choice(
        "What is the root cause category of this flaky test?",
        [rc.value for rc in FlakeRootCause if rc != FlakeRootCause.UNKNOWN],
        context,
        default=FlakeRootCause.ASYNC_TIMING.value,
    )
    root_cause = FlakeRootCause(laya_result.value)

    # Generate fix for classified root cause
    fix_desc, fix_patch = fix_generator.generate_fix(root_cause, test_source)

    return FlakeReport(
        report_id=report_id,
        test_id=test_id,
        root_cause=root_cause,
        root_cause_confidence=laya_result.confidence,
        fix_description=fix_desc,
        fix_patch=fix_patch,
        summary={
            "logs_analysed": len(logs),
            "pattern_signal": pat_sig.to_dict(),
            "code_signal": code_sig.to_dict(),
            "ordering_signal": ord_sig.to_dict(),
            "laya_source": laya_result.source,
        },
    )


async def _noop_code() -> code_agent.CodeSignal:
    return code_agent.CodeSignal()
