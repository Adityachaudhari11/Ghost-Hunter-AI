"""Code-review (Module A) schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Finding


class ArchitectureRule(BaseModel):
    rule_id: str  # e.g. database.repository_only
    title: str
    source: str  # e.g. ARCHITECTURE.md:12 — required, no invented rules
    forbidden_patterns: list[str] = Field(default_factory=list)
    required_patterns: list[str] = Field(default_factory=list)
    severity: str = "high"


class ChangedFile(BaseModel):
    path: str
    added_lines: list[tuple[int, str]] = Field(default_factory=list)  # (new_lineno, text)
    hunks: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    repo: str = ""
    pr_number: int = 0
    diff_text: str = ""  # unified diff; CLI/workflow can pass directly
    repo_dir: str = ""  # local checkout for full-file AST + dependency manifests


class ReviewReport(BaseModel):
    review_id: str
    findings: list[Finding] = Field(default_factory=list)
    correlated: list[dict] = Field(default_factory=list)  # risk correlator output
    summary: dict = Field(default_factory=dict)
