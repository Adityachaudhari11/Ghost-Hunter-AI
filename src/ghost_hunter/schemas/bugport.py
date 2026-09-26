"""BugPort schemas — production snapshot + reproduction harness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BugSnapshot(BaseModel):
    """PII-masked production snapshot captured by the BugPort sidecar."""
    snapshot_id: str
    git_sha: str = ""
    service: str = ""
    timestamp: str = ""
    # Call stack — no PII
    call_stack: list[str] = Field(default_factory=list)
    # DB query results — PII-masked (values replaced with type placeholders)
    db_query_results: list[dict] = Field(default_factory=list)
    # Environment spec — safe subset
    env_spec: dict[str, str] = Field(default_factory=dict)
    # In-memory state — relevant objects only, PII-masked
    state_snapshot: dict = Field(default_factory=dict)
    # Laya classification: which fields are bug-relevant
    relevant_fields: list[str] = Field(default_factory=list)


class BugPortRequest(BaseModel):
    snapshot_id: str = ""
    snapshot: BugSnapshot | None = None  # inline for demo
    store_path: str = "./reports/bugport-snapshots"


class ReproductionHarness(BaseModel):
    report_id: str
    snapshot_id: str = ""
    git_sha: str = ""
    env_file: str = ""          # .env.bugport contents
    db_fixture_sql: str = ""    # SQL to seed exact rows
    state_init_code: str = ""   # Python code to init in-memory state
    run_command: str = ""       # command to run the reproduction
    reproduced: bool = False
    summary: dict = Field(default_factory=dict)
