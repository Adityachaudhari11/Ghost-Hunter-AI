"""CausalTrace orchestrator pipeline — 3 parallel agents + Laya + synthesizer."""

from __future__ import annotations

import asyncio
import uuid

from ..agents.causaltrace import (
    git_agent,
    synthesizer,
    ticket_agent,
    trace_agent,
)
from ..core.config import Settings
from ..schemas.causaltrace import CausalReport, CausalTraceRequest


async def run_causaltrace(request: CausalTraceRequest) -> CausalReport:
    """Full CausalTrace flow:
    1. Three agents run in parallel (fan-out):
       TraceAgent  — fetch/parse distributed trace
       GitAgent    — git log on affected module
       TicketAgent — fetch linked issue context
    2. Laya Score: rank commits by likelihood of being root cause
    3. Synthesizer: compose causal narrative + fix + regression test
    """
    report_id = f"ct-{uuid.uuid4().hex[:8]}"
    settings = Settings()

    # Fan-out: all 3 subagents run simultaneously
    trace_task = trace_agent.run(request)
    git_task = git_agent.run(
        repo_dir="",          # will use demo data; real flow passes repo checkout
        affected_service=request.affected_service,
    )
    ticket_task = ticket_agent.run(
        repo=request.repo,
        token=settings.github_token,
    )
    trace, commits, ticket = await asyncio.gather(trace_task, git_task, ticket_task)

    # Synthesize (includes Laya scoring inside)
    report = await synthesizer.synthesize(report_id, trace, commits, ticket)
    return report
