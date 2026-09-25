"""FastAPI backend. Source of truth; frontend never makes security decisions."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .v1 import pentest as pentest_routes
from .v1 import reviews as review_routes

app = FastAPI(title="Ghost-Hunter-AI", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(review_routes.router, prefix="/api/v1")
app.include_router(pentest_routes.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
