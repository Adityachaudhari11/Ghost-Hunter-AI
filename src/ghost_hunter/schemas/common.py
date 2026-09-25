"""Shared finding / evidence contracts.

All agents (CLI, API, GitHub Action, workflow import) use these models,
so integration is seamless: same Pydantic objects in, same JSON out.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    REQUIRES_REVIEW = "requires_review"
    ACKNOWLEDGED = "acknowledged"
    IGNORED = "ignored"
    FIXED = "fixed"


class Evidence(BaseModel):
    """One piece of supporting evidence. Never invented by LLM."""

    kind: str = Field(description="e.g. registry_lookup, ast_node, rule_citation, code_location, log_ref")
    description: str
    ref: str = ""  # file:line, URL, log path, registry response snippet
    data: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    """Common evidence format for both modules (see spec section 15)."""

    finding_id: str = Field(description="Stable ID e.g. GH-001")
    source: str = Field(description="Agent name e.g. dependency_agent")
    module: str = Field(description="dependency|blueprint|ghost_path|reuse|coverage|failure|evidence|consistency|correlator")
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0, description="Model/agent confidence, NOT proof of security")
    file: str = ""
    line: int = 0
    rule: str = ""  # rule id or check id that was expected
    observed: str = Field(description="What happened")
    evidence: list[Evidence] = Field(default_factory=list)
    suggestion: str = Field(description="What the developer should investigate")
    status: FindingStatus = FindingStatus.REQUIRES_REVIEW
    uncertainty: str = Field(default="", description="What remains uncertain")

    def answers_six_questions(self) -> bool:
        """Evidence Engine gate: what/where/expected/evidence/uncertain/investigate."""
        return all(
            [
                bool(self.observed),
                bool(self.file or self.rule),
                bool(self.rule or self.source),
                len(self.evidence) > 0,
                bool(self.suggestion),
            ]
        )
