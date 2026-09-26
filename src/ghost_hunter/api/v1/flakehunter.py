"""FlakeHunter API — POST /flakehunter/run, GET /flakehunter/{report_id}."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...orchestrator.flakehunter_pipeline import run_flakehunter
from ...schemas.flakehunter import CIRunLog, FlakeReport

router = APIRouter(prefix="/flakehunter", tags=["FlakeHunter"])
_store: dict[str, FlakeReport] = {}


class FlakeHunterIn(BaseModel):
    test_id: str
    logs: list[CIRunLog] = []
    test_source: str = ""   # raw source of the flaky test file


@router.post("/run", response_model=FlakeReport)
async def run_flakehunter_endpoint(body: FlakeHunterIn) -> FlakeReport:
    report = await run_flakehunter(body.test_id, body.logs, body.test_source)
    _store[report.report_id] = report
    return report


@router.get("/{report_id}", response_model=FlakeReport)
async def get_flakehunter_report(report_id: str) -> FlakeReport:
    return _store[report_id]
