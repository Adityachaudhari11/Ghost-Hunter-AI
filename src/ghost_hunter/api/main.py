"""FastAPI backend. Source of truth; frontend never makes security decisions."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .v1 import bugport as bugport_routes
from .v1 import causaltrace as causaltrace_routes
from .v1 import flakehunter as flakehunter_routes
from .v1 import mutaci as mutaci_routes
from .v1 import pentest as pentest_routes
from .v1 import repos as repo_routes
from .v1 import reviews as review_routes

app = FastAPI(title="Ghost-Hunter-AI (GhostHunter / BugBridge)", version="0.2.0", docs_url="/docs", openapi_url="/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Original modules
app.include_router(review_routes.router, prefix="/api/v1")
app.include_router(pentest_routes.router, prefix="/api/v1")
app.include_router(repo_routes.router, prefix="/api/v1")

# GhostHunter / BugBridge modules
app.include_router(mutaci_routes.router, prefix="/api/v1")
app.include_router(flakehunter_routes.router, prefix="/api/v1")
app.include_router(causaltrace_routes.router, prefix="/api/v1")
app.include_router(bugport_routes.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
