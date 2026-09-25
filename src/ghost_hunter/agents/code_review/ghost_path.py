"""Ghost Path / exception auditor (Module A3). Pure AST + regex, no LLM needed."""

from __future__ import annotations

import ast
import re

from ...schemas.common import Evidence, Finding, Severity
from ...schemas.review import ChangedFile

TODO_RE = re.compile(r"TODO|FIXME|XXX|handle (failure|error|exception)", re.I)
NOT_IMPL = re.compile(r"raise\s+NotImplementedError")
JS_EMPTY_CATCH = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}")
JS_THEN_CATCH_EMPTY = re.compile(r"\.catch\s*\(\s*(\(\s*\)|[^)]*=>\s*\{\s*\})\s*\)")


def _finding(file: str, line: int, observed: str, snippet: str, severity: Severity, conf: float) -> Finding:
    return Finding(
        finding_id="GH-000",
        source="ghost_path_agent",
        module="ghost_path",
        severity=severity,
        confidence=conf,
        file=file,
        line=line,
        rule="error_handling.no_swallow",
        observed=observed,
        evidence=[Evidence(kind="ast_node", description="Suspicious failure handling", ref=f"{file}:{line}", data={"snippet": snippet[:500]})],
        suggestion="Log the error and either re-raise, map to a domain error, or handle explicitly; avoid silent fallback.",
        uncertainty="Some fallbacks are intentional (e.g. optional cache); confirm with owner.",
    )


def analyze_python_source(source: str, file: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            lineno = getattr(node, "lineno", 0)
            body = node.body
            snippet = "\n".join(lines[max(0, lineno - 2): lineno + 3])
            # bare except or except Exception with only pass
            is_bare = node.type is None
            is_broad = isinstance(node.type, ast.Name) and node.type.id == "Exception"
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                out.append(_finding(file, lineno, "Exception is caught and ignored (except: pass)", snippet, Severity.HIGH, 0.9 if not is_bare else 0.95))
            elif len(body) == 1 and isinstance(body[0], (ast.Return, ast.Expr)):
                ret = body[0]
                val = ""
                if isinstance(ret, ast.Return) and ret.value is not None:
                    try:
                        val = ast.unparse(ret.value)
                    except Exception:
                        val = "?"
                if val.strip() in ("{}", "[]", "None", "False", "0", '""', "''"):
                    out.append(_finding(file, lineno, f"Suspicious fallback '{val}' returned after exception hides failure", snippet, Severity.MEDIUM, 0.8))
            # TODO in handler
            seg = "\n".join(lines[lineno - 1: lineno + len(body) + 1])
            if TODO_RE.search(seg):
                out.append(_finding(file, lineno, "TODO/placeholder error handling left in except block", snippet, Severity.MEDIUM, 0.75))
            if is_bare:
                # already flagged if pass; also flag bare except generally
                if not (len(body) == 1 and isinstance(body[0], ast.Pass)):
                    out.append(_finding(file, lineno, "Bare except: catches everything including KeyboardInterrupt/SystemExit", snippet, Severity.MEDIUM, 0.8))
            _ = is_broad
        if isinstance(node, ast.Raise):
            lineno = getattr(node, "lineno", 0)
            try:
                txt = ast.unparse(node)
            except Exception:
                txt = ""
            if "NotImplementedError" in txt:
                out.append(_finding(file, lineno, "raise NotImplementedError left in new code", txt, Severity.MEDIUM, 0.85))
    return out


def analyze_js_text(text: str, file: str) -> list[Finding]:
    out: list[Finding] = []
    for i, line in enumerate(text.splitlines(), 1):
        if JS_EMPTY_CATCH.search(line) or JS_THEN_CATCH_EMPTY.search(line):
            out.append(_finding(file, i, "Empty catch block swallows async/sync errors", line.strip(), Severity.HIGH, 0.85))
        if re.search(r"catch\s*\([^)]*\)\s*\{\s*return\s+(\{\}|\[\]|null|false)", line):
            out.append(_finding(file, i, "Suspicious fallback returned from catch hides failure", line.strip(), Severity.MEDIUM, 0.8))
    return out


async def run(files: list[ChangedFile], full_sources: dict[str, str] | None = None) -> list[Finding]:
    """Prefer full file sources; fall back to added-line regex scan."""
    full_sources = full_sources or {}
    out: list[Finding] = []
    for f in files:
        src = full_sources.get(f.path)
        if src is not None:
            if f.path.endswith(".py"):
                out.extend(analyze_python_source(src, f.path))
            elif f.path.endswith((".js", ".ts", ".tsx", ".jsx")):
                out.extend(analyze_js_text(src, f.path))
            continue
        # fallback: scan added lines only
        added = "\n".join(t for _, t in f.added_lines)
        if f.path.endswith(".py"):
            if re.search(r"except\s*(Exception)?\s*:\s*\n?\s*pass", added):
                out.append(_finding(f.path, f.added_lines[0][0] if f.added_lines else 0, "Exception is caught and ignored (except: pass) in added lines", added[:500], Severity.HIGH, 0.7))
            if "except" in added.lower() and re.search(r"return\s+(\{\}|\[\]|None|False|0)", added):
                out.append(_finding(f.path, f.added_lines[0][0] if f.added_lines else 0, "Suspicious fallback returned after exception hides failure (added lines)", added[:500], Severity.MEDIUM, 0.7))
            if NOT_IMPL.search(added):
                out.append(_finding(f.path, 0, "raise NotImplementedError left in new code", added[:300], Severity.MEDIUM, 0.8))
            if TODO_RE.search(added) and "except" in added.lower():
                out.append(_finding(f.path, 0, "TODO/placeholder error handling in added lines", added[:300], Severity.MEDIUM, 0.65))
        else:
            out.extend(analyze_js_text(added, f.path))
    return out
