"""Tests for FlakeHunter module — pattern/code/ordering agents + Laya + fix generator."""

from __future__ import annotations

import asyncio

from src.ghost_hunter.agents.flakehunter.code_agent import run as code_run
from src.ghost_hunter.agents.flakehunter.fix_generator import generate_fix
from src.ghost_hunter.agents.flakehunter.pattern_agent import run as pattern_run
from src.ghost_hunter.orchestrator.flakehunter_pipeline import run_flakehunter
from src.ghost_hunter.schemas.flakehunter import CIRunLog, FlakeRootCause


_ASYNC_LOGS = [
    CIRunLog(test_id="test_auth", run_index=1, status="fail", log_excerpt="setTimeout timed out after 200ms"),
    CIRunLog(test_id="test_auth", run_index=2, status="pass", log_excerpt=""),
    CIRunLog(test_id="test_auth", run_index=3, status="fail", log_excerpt="waitFor() exceeded — timing issue"),
]

_ASYNC_SOURCE = (
    "describe('auth', () => {\n"
    "  it('should login', async () => {\n"
    "    const user = userService.create({ email: 't@t.com' });\n"
    "    setTimeout(() => { authStore.reset(); }, 200);\n"
    "  });\n"
    "});\n"
)


def test_pattern_agent_detects_timing():
    sig = asyncio.run(pattern_run(_ASYNC_LOGS))
    assert sig.timing_hits >= 2


def test_code_agent_detects_timeout():
    sig = asyncio.run(code_run(_ASYNC_SOURCE, "test_auth.js"))
    assert sig.hardcoded_timeouts or sig.missing_awaits


def test_fix_generator_async_timing():
    desc, patched = generate_fix(FlakeRootCause.ASYNC_TIMING, _ASYNC_SOURCE)
    assert "waitFor" in patched or "pattern not found" in desc


def test_fix_generator_unknown_is_advisory():
    desc, patched = generate_fix(FlakeRootCause.UNKNOWN, "some_source")
    assert "manual review" in desc.lower()
    assert patched == "some_source"


def test_flakehunter_pipeline_returns_report():
    report = asyncio.run(run_flakehunter("test_auth", _ASYNC_LOGS, _ASYNC_SOURCE))
    assert report.report_id.startswith("flake-")
    assert report.test_id == "test_auth"
    assert report.root_cause in FlakeRootCause.__members__.values()
    assert 0.0 <= report.root_cause_confidence <= 1.0
    assert isinstance(report.fix_description, str)
