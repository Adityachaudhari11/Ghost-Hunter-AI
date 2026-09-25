"""Review API: POST /reviews accepts diff or PR reference."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...core.config import Settings
from ...orchestrator.bob_adapter import BobOrchestrator
from ...schemas.review import ReviewReport

router = APIRouter()
_store: dict[str, ReviewReport] = {}


class ReviewIn(BaseModel):
    diff_text: str = ""
    repo_dir: str = ""
    repo: str = ""
    pr_number: int = 0


@router.post("/reviews", response_model=ReviewReport)
async def create_review(body: ReviewIn) -> ReviewReport:
    orch = BobOrchestrator(Settings())
    report = await orch.review(body.diff_text, body.repo_dir)
    _store[report.review_id] = report
    return report


@router.get("/reviews/{review_id}", response_model=ReviewReport)
async def get_review(review_id: str) -> ReviewReport:
    return _store[review_id]


@router.get("/findings/{finding_id}")
async def get_finding(finding_id: str) -> dict:
    for rep in _store.values():
        for f in rep.findings:
            if f.finding_id == finding_id:
                return f.model_dump()
    return {"error": "not found"}
