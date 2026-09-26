"""CausalTrace API — POST /causaltrace/run, GET /causaltrace/{report_id}."""

from __future__ import annotations

from fastapi import APIRouter

from ...orchestrator.causaltrace_pipeline import run_causaltrace
from ...schemas.causaltrace import CausalReport, CausalTraceRequest

router = APIRouter(prefix="/causaltrace", tags=["CausalTrace"])
_store: dict[str, CausalReport] = {}


@router.post("/run", response_model=CausalReport)
async def run_causaltrace_endpoint(body: CausalTraceRequest) -> CausalReport:
    report = await run_causaltrace(body)
    _store[report.report_id] = report
    return report


@router.get("/{report_id}", response_model=CausalReport)
async def get_causaltrace_report(report_id: str) -> CausalReport:
    return _store[report_id]
