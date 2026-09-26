"""MutaCI API — POST /mutaci/run, GET /mutaci/{report_id}."""

from __future__ import annotations

from fastapi import APIRouter

from ...orchestrator.mutaci_pipeline import run_mutaci
from ...schemas.mutaci import MutaCIReport, MutaCIRequest

router = APIRouter(prefix="/mutaci", tags=["MutaCI"])
_store: dict[str, MutaCIReport] = {}


@router.post("/run", response_model=MutaCIReport)
async def run_mutaci_endpoint(body: MutaCIRequest) -> MutaCIReport:
    report = await run_mutaci(body)
    _store[report.report_id] = report
    return report


@router.get("/{report_id}", response_model=MutaCIReport)
async def get_mutaci_report(report_id: str) -> MutaCIReport:
    return _store[report_id]
