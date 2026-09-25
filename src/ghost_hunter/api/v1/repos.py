"""Repo review API: gray-box proof run for a GitHub repo link (github.com only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.config import Settings
from ...ingesters.github_repo import materialize
from ...schemas.review import ReviewReport
from ...testing.graybox import prove_repo

router = APIRouter()
_store: dict[str, ReviewReport] = {}


class RepoIn(BaseModel):
    repo_url: str
    branch: str = ""


@router.post("/repo-reviews", response_model=ReviewReport)
async def create_repo_review(body: RepoIn) -> ReviewReport:
    settings = Settings()
    token = settings.github_token or None
    if token and "REPLACE_ME" in token:
        token = None
    try:
        root, cleanup = materialize(body.repo_url, body.branch or None, token=token)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    try:
        report = await prove_repo(root)
    finally:
        cleanup()
    _store[report.review_id] = report
    return report


@router.get("/repo-reviews/{review_id}", response_model=ReviewReport)
async def get_repo_review(review_id: str) -> ReviewReport:
    return _store[review_id]
