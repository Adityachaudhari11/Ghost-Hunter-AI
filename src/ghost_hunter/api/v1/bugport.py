"""BugPort API — POST /bugport/run, GET /bugport/{report_id}."""

from __future__ import annotations

from fastapi import APIRouter

from ...orchestrator.bugport_pipeline import run_bugport
from ...schemas.bugport import BugPortRequest, ReproductionHarness

router = APIRouter(prefix="/bugport", tags=["BugPort"])
_store: dict[str, ReproductionHarness] = {}


@router.post("/run", response_model=ReproductionHarness)
async def run_bugport_endpoint(body: BugPortRequest) -> ReproductionHarness:
    harness = await run_bugport(body)
    _store[harness.report_id] = harness
    return harness


@router.get("/{report_id}", response_model=ReproductionHarness)
async def get_bugport_report(report_id: str) -> ReproductionHarness:
    return _store[report_id]
