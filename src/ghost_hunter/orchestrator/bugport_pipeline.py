"""BugPort orchestrator pipeline — 3 parallel agents + reproduction harness."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from ..agents.bugport import data_agent, environment_agent, state_agent
from ..schemas.bugport import BugPortRequest, BugSnapshot, ReproductionHarness


async def run_bugport(request: BugPortRequest) -> ReproductionHarness:
    """Full BugPort flow:
    1. Load snapshot from store or inline body
    2. Three agents run in parallel (fan-out):
       EnvironmentAgent — generate .env.bugport
       DataAgent        — generate SQL fixture
       StateAgent       — reconstruct in-memory state (Laya PII gate)
    3. Assemble reproduction harness
    """
    report_id = f"bp-{uuid.uuid4().hex[:8]}"
    snapshot = _load_snapshot(request)
    if snapshot is None:
        return ReproductionHarness(
            report_id=report_id,
            summary={"error": "No snapshot found — provide snapshot_id or inline snapshot"},
        )

    # Fan-out: all 3 subagents run simultaneously
    env_task = environment_agent.run(snapshot)
    data_task = data_agent.run(snapshot)
    state_task = state_agent.run(snapshot)
    env_file, db_fixture, (state_code, relevant_fields) = await asyncio.gather(
        env_task, data_task, state_task
    )

    run_cmd = (
        f"git checkout {snapshot.git_sha} && "
        "cp .env.bugport .env && "
        "python -m pytest tests/bugport_repro.py -v"
    )

    return ReproductionHarness(
        report_id=report_id,
        snapshot_id=snapshot.snapshot_id,
        git_sha=snapshot.git_sha,
        env_file=env_file,
        db_fixture_sql=db_fixture,
        state_init_code=state_code,
        run_command=run_cmd,
        reproduced=bool(relevant_fields or db_fixture.strip() != "-- No DB query results in snapshot"),
        summary={
            "service": snapshot.service,
            "relevant_state_fields": relevant_fields,
            "has_db_fixture": "INSERT" in db_fixture,
            "call_stack_depth": len(snapshot.call_stack),
        },
    )


def _load_snapshot(request: BugPortRequest) -> BugSnapshot | None:
    """Load snapshot from inline body or from store path."""
    if request.snapshot:
        return request.snapshot
    if request.snapshot_id:
        store = Path(request.store_path)
        snap_file = store / f"{request.snapshot_id}.json"
        if snap_file.is_file():
            try:
                data = json.loads(snap_file.read_text(encoding="utf-8"))
                return BugSnapshot(**data)
            except Exception:
                return None
    return _demo_snapshot()


def _demo_snapshot() -> BugSnapshot:
    """Pre-recorded demo snapshot — payment service race condition."""
    return BugSnapshot(
        snapshot_id="snap-demo-001",
        git_sha="deadbeef447",
        service="payment-service",
        timestamp="2025-01-26T03:17:42Z",
        call_stack=[
            "payment_service.checkout.charge_payment:42",
            "payment_service.checkout.process:28",
            "payment_service.api.POST /checkout:15",
        ],
        db_query_results=[
            {"__table__": "users", "id": 9912, "email": "guest@example.com", "payment_method_id": None},
            {"__table__": "carts", "id": 5541, "user_id": 9912, "total": 149},
        ],
        env_spec={
            "APP_ENV": "production",
            "DB_POOL_SIZE": "10",
            "PAYMENT_GATEWAY": "stripe",
            "LOG_LEVEL": "info",
        },
        state_snapshot={
            "current_user_id": 9912,
            "cart_id": 5541,
            "payment_method": None,
            "is_guest": True,
        },
    )
