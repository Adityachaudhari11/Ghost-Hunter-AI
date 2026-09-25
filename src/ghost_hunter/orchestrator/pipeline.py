"""Orchestrator pipeline. Single entry for CLI, API, GHA, workflow import.

Bob 2.0 is used as fan-out/fan-in when configured; otherwise asyncio.
Independent agents run in parallel.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from ..agents.code_review import blueprint as blueprint_agent
from ..agents.code_review import dependency as dependency_agent
from ..agents.code_review import ghost_path as ghost_path_agent
from ..agents.code_review import reuse as reuse_agent
from ..agents.pentest import consistency as consistency_agent
from ..agents.pentest import coverage as coverage_agent
from ..agents.pentest import evidence_quality as evidence_agent
from ..agents.pentest import failure as failure_agent
from ..agents.pentest import recovery as recovery_agent
from ..core.evidence import validate_findings
from ..core.risk_correlator import correlate
from ..ingesters.context import load_rules, read_manifests, top_level_modules
from ..ingesters.diff import parse_diff
from ..schemas.common import Finding
from ..schemas.pentest import ReliabilityReport, ToolCall
from ..schemas.review import ReviewReport


def _full_sources(repo_dir: str, files: list) -> tuple[dict[str, str], list[dict]]:
    """Read full files for AST; build existing function index for reuse."""
    sources: dict[str, str] = {}
    index: list[dict] = []
    if not repo_dir:
        return sources, index
    root = Path(repo_dir)
    for f in files:
        p = root / f.path
        if p.is_file() and p.suffix == ".py":
            try:
                src = p.read_text(encoding="utf-8", errors="ignore")
                sources[f.path] = src
            except OSError:
                continue
    # index all repo .py functions (cheap for demo; FAISS later for scale)
    for p in root.rglob("*.py"):
        if ".venv" in str(p) or "__pycache__" in str(p):
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for fn in reuse_agent.extract_functions_py(src):
            index.append({"name": fn["name"], "file": str(p.relative_to(root)).replace("\\", "/"), "line": fn["line"], "code": fn["code"]})
    return sources, index


async def run_code_review(diff_text: str, repo_dir: str = "", review_id: str = "") -> ReviewReport:
    files = parse_diff(diff_text)
    rules = load_rules(repo_dir) if repo_dir else load_rules(".")
    manifests = read_manifests(repo_dir) if repo_dir else {}
    known_local = top_level_modules(repo_dir) if repo_dir else set()
    sources, index = _full_sources(repo_dir, files)

    dep_t = dependency_agent.run(files, manifests, None, known_local)
    bp_t = blueprint_agent.run(files, rules, sources)
    ghost_t = ghost_path_agent.run(files, sources)
    reuse_t = reuse_agent.run(files, sources, index)
    dep, bp, ghost, reuse = await asyncio.gather(dep_t, bp_t, ghost_t, reuse_t)

    all_findings: list[Finding] = validate_findings([*dep, *bp, *ghost, *reuse])
    correlated = correlate(all_findings)
    sev = {}
    for f in all_findings:
        sev[f.severity.value] = sev.get(f.severity.value, 0) + 1
    return ReviewReport(
        review_id=review_id or f"rev-{uuid.uuid4().hex[:8]}",
        findings=all_findings,
        correlated=correlated,
        summary={"total": len(all_findings), "by_severity": sev, "files": len(files)},
    )


async def run_pentest_audit(
    plan: list[str],
    runs: list[list[ToolCall]],
    target: str = "local-test-app",
    retry_fn=None,
) -> ReliabilityReport:
    statuses, cov_findings = await coverage_agent.run(plan, runs)
    fail_findings = await failure_agent.run(runs)
    quality, ev_findings = await evidence_agent.run(plan, runs)
    issues = await consistency_agent.run(plan, runs)
    cons_findings = consistency_agent.to_findings(issues)

    cov = coverage_agent.coverage(statuses, quality)
    missing_failed = [c for c, s in statuses.items() if s in ("NOT_EXECUTED", "FAILED", "SKIPPED")]
    recovery = await recovery_agent.run(missing_failed, retry_fn=retry_fn)

    findings = validate_findings([*cov_findings, *fail_findings, *ev_findings, *cons_findings])
    verified = sum(1 for c in plan if statuses.get(c) == "COMPLETED" and quality.get(c) in ("STRONG", "WEAK"))
    unverified = len(plan) - verified
    _ = target
    return ReliabilityReport(
        report_id=f"rel-{uuid.uuid4().hex[:8]}",
        coverage=cov,
        statuses=statuses,
        evidence_quality=quality,
        inconsistencies=issues,
        recovery=recovery,
        findings=findings,
        verified_count=verified,
        unverified_count=unverified,
    )
