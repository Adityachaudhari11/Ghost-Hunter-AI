"""Gray-box proof tester: repo dir -> full-repo evidence-backed verdicts.

Gray-box = source + docs visible, runtime/env NOT assumed. Every claim cites
file:line + method + reproducible proof. Unprovable items are reported as
limits, never as clean verdicts.

Covers: dependency/API hallucination, unwanted code (architecture violations,
ghost paths, duplication) across the whole tree — including the main branch,
not just a diff.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..agents.code_review import blueprint as blueprint_agent
from ..agents.code_review import dependency as dependency_agent
from ..agents.code_review import ghost_path as ghost_path_agent
from ..agents.code_review import reuse as reuse_agent
from ..agents.code_review.dependency import Checker
from ..core.evidence import validate_findings
from ..core.risk_correlator import correlate
from ..ingesters.context import load_rules, read_manifests, top_level_modules
from ..schemas.common import Finding
from ..schemas.review import ChangedFile, ReviewReport

SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".tox", ".pytest_cache", "reports", ".idea", ".vscode"}

LIMITS = (
    "Gray-box limits: source + docs visible; runtime behavior, private registries, "
    "and live exploitability are NOT proven. UNVERIFIED means 're-check', not 'malicious'."
)


def collect_sources(root: str | Path) -> dict[str, str]:
    """Relative posix path -> content for reviewable source files."""
    base = Path(root)
    out: dict[str, str] = {}
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.suffix not in SOURCE_EXT:
            continue
        rel = p.relative_to(base).as_posix()
        if any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(base).parts[:-1]):
            continue
        try:
            out[rel] = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return out


def _build_index(sources: dict[str, str]) -> list[dict]:
    index: list[dict] = []
    for rel, content in sources.items():
        if not rel.endswith(".py"):
            continue
        for fn in reuse_agent.extract_functions_py(content):
            index.append({"name": fn["name"], "file": rel, "line": fn["line"], "code": fn["code"]})
    return index


async def prove_repo(
    repo_dir: str | Path,
    checker: Checker | None = None,
    review_id: str = "",
) -> ReviewReport:
    """Full-tree proof run. checker injects registry answers (offline-safe tests)."""
    root = Path(repo_dir)
    sources = collect_sources(root)
    files = [
        ChangedFile(path=rel, added_lines=list(enumerate(content.splitlines(), 1)), hunks=["full-repo-scan"])
        for rel, content in sources.items()
    ]
    rules = load_rules(root)
    manifests = read_manifests(root)
    known_local = top_level_modules(root)
    index = _build_index(sources)

    dep = await dependency_agent.run(files, manifests, checker, known_local)
    bp = await blueprint_agent.run(files, rules, sources)
    ghost = await ghost_path_agent.run(files, sources)
    reuse = await reuse_agent.run(files, sources, index)

    findings: list[Finding] = validate_findings([*dep, *bp, *ghost, *reuse])
    correlated = correlate(findings)
    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
    return ReviewReport(
        review_id=review_id or f"proof-{uuid.uuid4().hex[:8]}",
        findings=findings,
        correlated=correlated,
        summary={
            "method": "graybox-full-repo",
            "files_scanned": len(sources),
            "total": len(findings),
            "by_severity": by_sev,
            "limits": LIMITS,
        },
    )


def format_proof_markdown(report: ReviewReport) -> str:
    s = report.summary
    lines = [
        f"# Gray-box proof: `{report.review_id}`",
        "",
        f"Files scanned: {s.get('files_scanned', 0)} | Findings: {s.get('total', 0)} {s.get('by_severity', {})}",
        "",
    ]
    for f in report.findings:
        lines.append(
            f"- **[{f.severity.value.upper()}]** `{f.file}:{f.line}` [{f.module}] {f.observed} (conf {f.confidence:.2f})"
        )
        for e in f.evidence[:2]:
            lines.append(f"  - proof: {e.kind} → {e.ref}")
    lines += ["", f"> {LIMITS}"]
    if report.correlated:
        lines.append("")
        for c in report.correlated:
            lines.append(f"Correlated `{c['file']}` boost +{c['priority_boost']}: {'; '.join(c['reasons'])}")
    return "\n".join(lines)
