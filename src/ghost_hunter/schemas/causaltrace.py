"""CausalTrace schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    """One distributed trace span."""
    span_id: str = ""
    service: str = ""
    operation: str = ""
    duration_ms: int = 0
    status: str = "ok"   # "ok" | "error" | "degraded"
    error_message: str = ""


class GitCommit(BaseModel):
    """Relevant git commit near the incident."""
    sha: str = ""
    author: str = ""
    message: str = ""
    timestamp: str = ""
    pr_number: int = 0
    files_changed: list[str] = Field(default_factory=list)
    diff_excerpt: str = ""


class TicketContext(BaseModel):
    """Linked issue/ticket intent."""
    ticket_id: str = ""
    title: str = ""
    description: str = ""
    acceptance_criteria: str = ""
    scope: str = ""  # e.g. "logged-in users only"


class CausalTraceRequest(BaseModel):
    # At least one signal source required
    sentry_url: str = ""
    datadog_alert_id: str = ""
    k8s_event: str = ""
    # Optional enrichment
    repo: str = ""
    affected_service: str = ""
    incident_timestamp: str = ""


class CausalReport(BaseModel):
    report_id: str
    incident_summary: str = ""
    causal_narrative: str = ""       # The paragraph a senior SRE would write
    root_cause_commit: GitCommit | None = None
    root_cause_score: float = 0.0    # Laya score
    fix_description: str = ""
    fix_patch: str = ""
    regression_test: str = ""
    trace_chain: list[TraceSpan] = Field(default_factory=list)
    relevant_commits: list[GitCommit] = Field(default_factory=list)
    ticket: TicketContext | None = None
    summary: dict = Field(default_factory=dict)
