"""Tests for CausalTrace module — trace/git/ticket agents + synthesizer."""

from __future__ import annotations

import asyncio

from src.ghost_hunter.agents.causaltrace.git_agent import _demo_commits
from src.ghost_hunter.agents.causaltrace.ticket_agent import _demo_ticket
from src.ghost_hunter.agents.causaltrace.trace_agent import _demo_trace
from src.ghost_hunter.agents.causaltrace.synthesizer import synthesize
from src.ghost_hunter.orchestrator.causaltrace_pipeline import run_causaltrace
from src.ghost_hunter.schemas.causaltrace import CausalTraceRequest


def test_demo_trace_returns_spans():
    spans = _demo_trace("payment-service")
    assert len(spans) == 3
    error_spans = [s for s in spans if s.status == "error"]
    assert len(error_spans) == 1
    assert "null" in error_spans[0].error_message.lower()


def test_demo_commits_returns_list():
    commits = _demo_commits()
    assert len(commits) >= 1
    assert commits[0].pr_number == 447
    assert "null" in commits[0].message.lower() or "null-check" in commits[0].message.lower()


def test_demo_ticket_has_scope():
    ticket = _demo_ticket()
    assert "logged-in" in ticket.scope.lower()


def test_synthesizer_produces_narrative():
    report = asyncio.run(synthesize(
        "ct-test-001",
        _demo_trace("payment-service"),
        _demo_commits(),
        _demo_ticket(),
    ))
    assert report.report_id == "ct-test-001"
    assert report.causal_narrative
    assert "PR" in report.causal_narrative or "commit" in report.causal_narrative.lower()
    assert report.root_cause_score > 0
    assert report.regression_test


def test_causaltrace_pipeline_demo():
    req = CausalTraceRequest(
        sentry_url="https://sentry.io/organizations/acme/issues/12345/",
        affected_service="payment-service",
    )
    report = asyncio.run(run_causaltrace(req))
    assert report.report_id.startswith("ct-")
    assert report.causal_narrative
    assert isinstance(report.trace_chain, list)
    assert len(report.trace_chain) > 0
