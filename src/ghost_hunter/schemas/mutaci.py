"""MutaCI schemas — PR-scoped mutation testing signal."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MutantResult(BaseModel):
    """One generated mutant and whether the test suite killed it."""
    mutant_id: str
    file: str
    line: int
    operator: str        # e.g. "AOR", "LCR", "UOI", "ROR"
    original: str        # original code fragment
    mutated: str         # mutated code fragment
    killed: bool
    killing_test: str = ""


class BehavioralGap(BaseModel):
    """A surviving mutant scored by Laya as a real behavioral gap."""
    mutant_id: str
    file: str
    line: int
    description: str     # plain-English explanation for developer
    impact_score: float  # Laya score 1–10
    suggested_test: str  # generated test description


class MutaCIRequest(BaseModel):
    diff_text: str = ""
    repo_dir: str = ""
    repo: str = ""
    pr_number: int = 0
    runner: str = "stub"  # mutmut | stryker | cosmic-ray | stub


class MutaCIReport(BaseModel):
    report_id: str
    total_mutants: int = 0
    killed_mutants: int = 0
    survived_mutants: int = 0
    mutation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    gaps: list[BehavioralGap] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
