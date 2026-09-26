"""Tests for BugPort module — snapshot, 3 agents, reproduction harness."""

from __future__ import annotations

import asyncio

from src.ghost_hunter.agents.bugport.data_agent import generate_sql_fixture
from src.ghost_hunter.agents.bugport.environment_agent import generate_env_file
from src.ghost_hunter.orchestrator.bugport_pipeline import _demo_snapshot, run_bugport
from src.ghost_hunter.schemas.bugport import BugPortRequest, BugSnapshot


def test_demo_snapshot_is_valid():
    snap = _demo_snapshot()
    assert snap.snapshot_id == "snap-demo-001"
    assert snap.git_sha == "deadbeef447"
    assert snap.service == "payment-service"
    assert snap.call_stack
    assert snap.state_snapshot.get("is_guest") is True


def test_env_agent_excludes_pii():
    from src.ghost_hunter.schemas.bugport import BugSnapshot
    snap = BugSnapshot(
        snapshot_id="snap-pii-test",
        git_sha="abc123",
        service="test-service",
        env_spec={
            "APP_ENV": "production",
            "DB_PASSWORD": "supersecretpassword",
            "API_KEY": "sk-1234secret",
            "LOG_LEVEL": "info",
        },
    )
    env_file = generate_env_file(snap)
    assert "APP_ENV" in env_file
    assert "LOG_LEVEL" in env_file
    # PII/secret key values must be excluded
    assert "supersecretpassword" not in env_file
    assert "sk-1234secret" not in env_file


def test_data_agent_generates_sql():
    snap = _demo_snapshot()
    sql = generate_sql_fixture(snap)
    assert "INSERT INTO" in sql
    assert "guest@example.com" not in sql
    assert "MASKED" in sql


def test_bugport_pipeline_returns_harness():
    req = BugPortRequest()  # no snapshot_id → uses demo snapshot
    harness = asyncio.run(run_bugport(req))
    assert harness.report_id.startswith("bp-")
    assert harness.snapshot_id == "snap-demo-001"
    assert harness.git_sha == "deadbeef447"
    assert harness.env_file
    assert harness.db_fixture_sql
    assert harness.state_init_code
    assert harness.run_command


def test_bugport_with_inline_snapshot():
    snap = _demo_snapshot()
    req = BugPortRequest(snapshot=snap)
    harness = asyncio.run(run_bugport(req))
    assert harness.snapshot_id == snap.snapshot_id
