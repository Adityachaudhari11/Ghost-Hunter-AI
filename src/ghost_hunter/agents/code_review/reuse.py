"""Internal reuse auditor (Module A4).

Deterministic token-based similarity (Jaccard + difflib) so it runs offline.
Optional embedding hook: pass `embed(text)->vector` for semantic re-rank;
without it, lexical score is used and confidence is capped.
"""

from __future__ import annotations

import ast
import difflib
import re
from typing import Callable

from ...schemas.common import Evidence, Finding, Severity
from ...schemas.review import ChangedFile

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _tokens(code: str) -> set[str]:
    toks: set[str] = set()
    for raw in _TOKEN.findall(code):
        low = raw.lower()
        toks.add(low)
        for part in re.split(r"_+", low):
            if len(part) > 2:
                toks.add(part)
    return {t for t in toks if len(t) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    jacc = len(ta & tb) / len(ta | tb)
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    return 0.5 * jacc + 0.5 * seq


def extract_functions_py(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = ast.get_source_segment(source, node) or ""
            out.append({"name": node.name, "line": getattr(node, "lineno", 0), "code": seg})
    return out


async def run(
    files: list[ChangedFile],
    full_sources: dict[str, str] | None = None,
    existing_index: list[dict] | None = None,
    embed: Callable[[str], list[float]] | None = None,
) -> list[Finding]:
    """existing_index: [{name, file, line, code}]. full_sources: path->content."""
    full_sources = full_sources or {}
    existing_index = existing_index or []
    out: list[Finding] = []
    for f in files:
        src = full_sources.get(f.path, "\n".join(t for _, t in f.added_lines))
        if not f.path.endswith(".py"):
            continue
        for fn in extract_functions_py(src):
            best: dict | None = None
            best_score = 0.0
            for ex in existing_index:
                if ex.get("name") == fn["name"] and ex.get("file") == f.path:
                    continue
                s = similarity(fn["code"], ex.get("code", ""))
                if s > best_score:
                    best_score, best = s, ex
            if best and best_score >= 0.70:
                sev = Severity.MEDIUM if best_score >= 0.82 else Severity.LOW
                conf = min(0.9, best_score) if embed else min(0.75, best_score)
                out.append(
                    Finding(
                        finding_id="GH-000",
                        source="reuse_agent",
                        module="reuse",
                        severity=sev,
                        confidence=round(conf, 2),
                        file=f.path,
                        line=fn["line"],
                        rule="reuse.prefer_utils",
                        observed=f"Possible duplicate: new '{fn['name']}()' resembles existing '{best.get('name')}()' ({best_score:.0%})",
                        evidence=[
                            Evidence(kind="code_location", description="Existing implementation", ref=f"{best.get('file')}:{best.get('line')}", data={"name": best.get("name")}),
                            Evidence(kind="similarity", description="Lexical similarity score", ref=f.path, data={"score": round(best_score, 3), "semantic": bool(embed)}),
                        ],
                        suggestion=f"Reuse {best.get('file')}:{best.get('name')} if semantics match; else document why a new copy is needed.",
                    )
                )
    return out
