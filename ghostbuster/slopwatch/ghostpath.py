"""Scanner 3 — Ghost Path & Exception Hunter.

Flags the "lazy" error handling LLMs love to write:

- ``except Exception: pass`` / bare ``except:`` / empty ``except`` blocks
- silent fallbacks: ``except ...: return None/False/[]/{}/''`` with no log
- placeholder comments: TODO / FIXME / "handle failure" / "not implemented"
  left inside handlers or fallback branches
- JS/TS: empty ``catch {}`` blocks and the same placeholder phrases

Python files are analysed with ``ast`` (precise); anything unparseable —
plus all JS/TS — falls back to regex so the hunter never misses a file.
"""

import ast
import os
import re
from pathlib import Path

PLACEHOLDER_RE = re.compile(
    r"(TODO|FIXME|XXX|HACK).{0,40}(handl|fail|error|exception|implement|later|todo)"
    r"|handle.{0,20}(failure|error).{0,20}(later|todo|not|missing)"
    r"|not\s+implemented|left\s+as\s+an?\s+exercise",
    re.IGNORECASE,
)
JS_EMPTY_CATCH_RE = re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}")
JS_CATCH_RE = re.compile(r"catch\s*(\([^)]*\))?\s*\{(.*?)\}", re.DOTALL)
SILENT_RETURNS = {"None", "False", "True", "[]", "{}", "''", '""', "0", "-1"}

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}


def _is_silent(node: ast.AST) -> bool:
    """True if an except-handler body does nothing observable."""
    if not node.body:
        return True
    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
        return True
    if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
        v = node.body[0].value
        if isinstance(v, ast.Constant) and isinstance(v.value, (str, type(None))):
            return True  # bare string / docstring-only handler
    if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
        r = node.body[0].value
        if r is None or (isinstance(r, ast.Constant) and r.value in (None, False, True, 0, -1, "", [], {})):
            return True
    return False


def _has_placeholder(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text or ""))


def scan_python_ghost_paths(path: Path, text: str) -> list[dict]:
    out: list[dict] = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for h in node.handlers:
            kind = "bare except:" if h.type is None else f"except {ast.unparse(h.type)}"
            snippet = ast.get_source_segment(text, h) or ""
            silent = _is_silent(h)
            placeholder = _has_placeholder(snippet)
            if silent or placeholder or (isinstance(h.type, ast.Name) and h.type.id == "Exception" and len(h.body) <= 1):
                if silent and isinstance(h.body[0] if h.body else None, ast.Pass):
                    sev, label = 8, "swallowed exception (pass)"
                elif silent:
                    sev, label = 7, "silent fallback return"
                elif placeholder:
                    sev, label = 6, "placeholder TODO in handler"
                else:
                    sev, label = 6, "over-broad except Exception"
                out.append({
                    "id": "", "scanner": "ghostpath", "severity": sev,
                    "file": str(path), "line": h.lineno,
                    "message": f"\U0001f47b Ghost path [{label}] — {kind} at line {h.lineno} hides failures.",
                    "code": (snippet.strip().splitlines() or [""])[0][:160],
                    "fix": "Log the error (logger.exception), narrow the exception type, "
                           "and return/re-raise an explicit error value.",
                })
    return out


def scan_text_ghost_paths(path: Path, text: str) -> list[dict]:
    """Regex fallback — covers JS/TS catch blocks and TODO placeholders."""
    out: list[dict] = []
    lines = text.splitlines()
    for m in JS_EMPTY_CATCH_RE.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        out.append({
            "id": "", "scanner": "ghostpath", "severity": 8,
            "file": str(path), "line": line,
            "message": "\U0001f47b Ghost path [empty catch] — errors vanish silently.",
            "code": "catch { }",
            "fix": "Log the error and handle or re-throw it explicitly.",
        })
    # non-empty catch blocks that only contain a placeholder comment
    for m in JS_CATCH_RE.finditer(text):
        body = m.group(2).strip()
        if body and not re.search(r"[{}]", body) and _has_placeholder(body):
            line = text.count("\n", 0, m.start()) + 1
            out.append({
                "id": "", "scanner": "ghostpath", "severity": 6,
                "file": str(path), "line": line,
                "message": "\U0001f47b Ghost path [placeholder TODO in catch] — failure unhandled.",
                "code": body.splitlines()[0][:160],
                "fix": "Implement the failure path: log + fallback or re-throw.",
            })
    # Python files that failed to parse still get placeholder/empty-handler scan
    if path.suffix.lower() == ".py":
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if re.match(r"except\b.*:\s*pass\s*(#.*)?$", s):
                out.append({
                    "id": "", "scanner": "ghostpath", "severity": 8,
                    "file": str(path), "line": i,
                    "message": "\U0001f47b Ghost path [swallowed exception] — `except: pass` hides failures.",
                    "code": s[:160],
                    "fix": "Log the error and handle or re-raise it.",
                })
    # bare TODO-handle-failure phrases anywhere (both languages)
    for i, line in enumerate(lines, 1):
        if _has_placeholder(line) and not any(f["line"] == i and f["file"] == str(path) for f in out):
            out.append({
                "id": "", "scanner": "ghostpath", "severity": 5,
                "file": str(path), "line": i,
                "message": "\U0001f47b Ghost path [unimplemented failure handling] — placeholder left in code.",
                "code": line.strip()[:160],
                "fix": "Implement the failure branch at least minimally (log + safe default).",
            })
    return out


def scan_ghost_paths(target: str) -> list[dict]:
    root = Path(target).resolve()
    findings: list[dict] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if p.suffix.lower() == ".py":
                findings.extend(scan_python_ghost_paths(p, text))
            findings.extend(scan_text_ghost_paths(p, text) if p.suffix.lower() != ".py"
                            else [x for x in scan_text_ghost_paths(p, text)
                                  if x["message"].startswith("\U0001f47b Ghost path [unimplemented")])
    for i, f in enumerate(findings, 1):
        f["id"] = f"GHOST-{i:02d}"
    return findings
