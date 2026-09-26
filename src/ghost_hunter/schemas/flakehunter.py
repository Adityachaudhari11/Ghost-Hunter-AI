"""FlakeHunter schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FlakeRootCause(str, Enum):
    ASYNC_TIMING  = "async_timing"
    STATE_POLLUTION = "state_pollution"
    PORT_COLLISION = "port_collision"
    TEST_ORDERING  = "test_ordering"
    ENVIRONMENT    = "environment"
    UNKNOWN        = "unknown"


class CIRunLog(BaseModel):
    """One CI test run log entry."""
    test_id: str
    run_index: int = 0
    status: str         # "pass" | "fail"
    duration_ms: int = 0
    log_excerpt: str = ""
    predecessor_test: str = ""  # test that ran immediately before


class FlakeReport(BaseModel):
    report_id: str
    test_id: str
    root_cause: FlakeRootCause = FlakeRootCause.UNKNOWN
    root_cause_confidence: float = 0.0
    fix_description: str = ""
    fix_patch: str = ""           # unified-diff style patch
    validated: bool = False
    validation_runs: int = 0
    validation_pass: int = 0
    summary: dict = Field(default_factory=dict)
