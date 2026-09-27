"""Scanner 1 — "Slop Squatting" & API Hallucination Registry.

Extracts every external import from the target (or PR diff) and verifies it:

1. Python (.py) via ``ast`` — ``import x`` / ``from x import y``.
2. JS/TS (.js/.jsx/.ts/.tsx) via regex — ``import .. from 'pkg'``,
   ``require('pkg')``, ``import('pkg')``.

Each top-level package is classified as stdlib/builtin, internal
(file exists in the repo), or external. External packages are checked
against the live registries:

- PyPI: https://pypi.org/pypi/<name>/json
- npm:  https://registry.npmjs.org/<name>/latest

A package that does not exist in its registry is flagged with the
critical red error::

    Warning: Likely AI Hallucination. High risk of supply chain attack.

Plus two best-effort extras (never crash the scan):

- typosquat heuristic: edit-distance <= 2 against a short popular-package
  list (e.g. ``requestes`` vs ``requests``) -> warn.
- hallucinated-method check (Python only): if the package is importable
  locally, ``hasattr`` every ``pkg.attr`` used in the file; a missing
  attribute is a hallucinated API.

Offline behaviour: if the network call fails, verdict is ``unknown``
instead of ``hallucinated`` — no false red errors without evidence.
"""

import ast
import importlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

# ── stdlib / builtin knowledge ─────────────────────────────────────────

try:
    _STDLIB = set(sys.stdlib_module_names)  # Python 3.10+
except AttributeError:  # pragma: no cover
    _STDLIB = {
        "os", "sys", "re", "json", "ast", "math", "time", "datetime",
        "pathlib", "typing", "collections", "itertools", "functools",
        "threading", "asyncio", "logging", "unittest", "http", "urllib",
        "hashlib", "random", "string", "io", "csv", "sqlite3", "argparse",
    }

_NODE_BUILTINS = {
    "fs", "path", "os", "http", "https", "url", "util", "events", "crypto",
    "stream", "child_process", "cluster", "assert", "buffer", "querystring",
    "node:test", "node:fs", "node:path",
}

# Short popular-package list for the typosquat heuristic.
_POPULAR_PY = {
    "requests", "numpy", "pandas", "flask", "django", "fastapi", "pytest",
    "sqlalchemy", "boto3", "pillow", "redis", "celery", "click", "pydantic",
}
_POPULAR_NPM = {
    "lodash", "axios", "express", "react", "chalk", "moment", "uuid",
    "commander", "typescript", "jest", "zod", "date-fns",
}

RED_FLAG = "Warning: Likely AI Hallucination. High risk of supply chain attack."

_TS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]"""
    r"""|require\s*\(\s*['"]([^'"]+)['"]\s*\)"""
    r"""|import\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)
_PYPI_URL = "https://pypi.org/pypi/{pkg}/json"
_NPM_URL = "https://registry.npmjs.org/{pkg}/latest"

_registry_cache: dict = {}


@dataclass
class ImportSite:
    package: str  # top-level package as imported
    full_name: str  # full dotted / raw specifier
    file: str
    line: int
    language: str  # "python" | "node"
    guarded: bool = False  # inside try/except ImportError (optional dep)
    typecheck: bool = False  # under `if TYPE_CHECKING:` (never runs)


# ── extraction ─────────────────────────────────────────────────────────

def extract_imports_from_file(path: Path) -> list[ImportSite]:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if suffix == ".py":
        return _extract_python(text, str(path))
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return _extract_node(text, str(path))
    return []


def _extract_python(text: str, fname: str) -> list[ImportSite]:
    sites: list[ImportSite] = []
    try:
        tree = ast.parse(text, filename=fname)
    except SyntaxError:
        return sites
    guarded, typecheck = _guarded_import_lines(tree)  # optional-dep / TYPE_CHECKING ranges
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = (a.name or "").split(".")[0]
                if top:
                    s = ImportSite(top, a.name, fname, node.lineno, "python")
                    s.guarded = node.lineno in guarded
                    s.typecheck = node.lineno in typecheck
                    sites.append(s)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import — internal by definition
            if node.module:
                top = node.module.split(".")[0]
                s = ImportSite(top, node.module, fname, node.lineno, "python")
                s.guarded = node.lineno in guarded
                s.typecheck = node.lineno in typecheck
                sites.append(s)
    return sites


def _guarded_import_lines(tree: ast.AST) -> tuple[set[int], set[int]]:
    """Return (guarded, typecheck) line sets.

    guarded: lines inside a try-statement that catches ImportError /
      ModuleNotFoundError (body, handlers, else and finally included —
      the whole statement is an optional-dependency construct, e.g.
      py2/3 fallback imports living in the except-handler itself).
    typecheck: lines under ``if TYPE_CHECKING:`` (never run at runtime).
    """
    guarded: set[int] = set()
    typecheck: set[int] = set()

    def is_import_guard(handler: ast.ExceptHandler) -> bool:
        if handler.type is None:
            return True
        names = set()
        if isinstance(handler.type, ast.Name):
            names = {handler.type.id}
        elif isinstance(handler.type, ast.Tuple):
            names = {e.id for e in handler.type.elts if isinstance(e, ast.Name)}
        return bool(names & {"ImportError", "ModuleNotFoundError", "Exception"})

    def span(stmts: list[ast.stmt]):
        for s in stmts:
            guarded.update(range(s.lineno, (s.end_lineno or s.lineno) + 1))

    def is_typechecking(test: ast.AST) -> bool:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(is_import_guard(h) for h in node.handlers):
            span(node.body)
            span(node.orelse)
            span(node.finalbody)
            for h in node.handlers:
                span(h.body)
        if isinstance(node, ast.If) and is_typechecking(node.test):
            for s in node.body:
                typecheck.update(range(s.lineno, (s.end_lineno or s.lineno) + 1))
    return guarded, typecheck


def _extract_node(text: str, fname: str) -> list[ImportSite]:
    sites: list[ImportSite] = []
    for m in _TS_IMPORT_RE.finditer(text):
        raw = m.group(1) or m.group(2) or m.group(3)
        if not raw:
            continue
        if raw.startswith((".", "/")):
            continue  # relative — internal
        if raw.startswith("@"):
            top = "/".join(raw.split("/")[:2])  # scoped: @scope/name
        else:
            top = raw.split("/")[0]
        line = text.count("\n", 0, m.start()) + 1
        sites.append(ImportSite(top, raw, fname, line, "node"))
    return sites


def collect_imports(target: Path, diff_files: "set[str] | None" = None) -> list[ImportSite]:
    """Walk target dir (or restrict to diff files) and collect imports."""
    sites: list[ImportSite] = []
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    skip_dirs = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() not in exts:
                continue
            if diff_files is not None and str(p.resolve()) not in diff_files:
                continue
            sites.extend(extract_imports_from_file(p))
    return sites


def parse_diff_files(diff_text: str, target: Path) -> "set[str] | None":
    """Return absolute paths of files touched by a unified diff, or None."""
    files: set[str] = set()
    for m in re.finditer(r"^\+\+\+\s+b/(.+)$", diff_text, re.M):
        files.add(str((target / m.group(1).strip()).resolve()))
    return files or None


# ── registry checks ────────────────────────────────────────────────────

def registry_exists(package: str, language: str, timeout: float = 5.0) -> "bool | None":
    """True = exists, False = definitely absent (404), None = unknown (offline)."""
    key = (language, package)
    if key in _registry_cache:
        return _registry_cache[key]
    url = (_PYPI_URL if language == "python" else _NPM_URL).format(pkg=package)
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            _registry_cache[key] = True
        elif r.status_code == 404:
            _registry_cache[key] = False
        else:
            _registry_cache[key] = None
    except Exception:
        _registry_cache[key] = None  # offline — refuse to accuse
    return _registry_cache[key]


def _edit_distance(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def typosquat_of(package: str, language: str) -> "str | None":
    base = package.split("/")[0].lstrip("@").lower()
    if language == "python":
        popular = _POPULAR_PY
    else:
        popular = {p.split("/")[-1] for p in _POPULAR_NPM}
    for pop in popular:
        if base != pop and _edit_distance(base, pop) <= 2 and len(base) >= 4:
            return pop
    return None


def _name_exists(mod, package: str, name: str) -> bool:
    """True if pkg.name is an attribute OR an (unimported) submodule."""
    if hasattr(mod, name):
        return True
    try:
        return importlib.util.find_spec(f"{package}.{name}") is not None
    except Exception:
        return False


def hallucinated_attrs(python_file: str, package: str) -> list[tuple[str, int]]:
    """Best-effort: (attr, line) used as pkg.X that the installed pkg lacks.

    Submodule-aware (unittest.mock counts as existing). Version skew between
    the scanned repo and the locally installed package can cause false
    alarms — callers must treat these as WARN, never BLOCK.
    """
    try:
        mod = importlib.import_module(package)
    except Exception:
        return []  # not installed — cannot judge, stay silent
    try:
        text = Path(python_file).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(text)
    except Exception:
        return []
    aliases: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if (a.name or "").split(".")[0] == package:
                    aliases[(a.asname or a.name.split(".")[0]).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == package:
                for a in node.names:
                    if a.name != "*" and not _name_exists(mod, package, a.name):
                        return [(a.name, node.lineno)]
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in aliases and not _name_exists(mod, package, node.attr):
                out.append((node.attr, node.lineno))
    return sorted(set(out))


# ── main scan ──────────────────────────────────────────────────────────

def _is_internal(package: str, language: str, target: Path) -> bool:
    if language == "python":
        cand = [
            target / f"{package}.py",
            target / package / "__init__.py",
            target / "src" / f"{package}.py",
        ]
    else:
        cand = [target / "src" / f"{package}.ts", target / "src" / f"{package}.js"]
    return any(c.exists() for c in cand)


def scan_hallucinations(target: str, diff_text: str = "") -> list[dict]:
    """Scan target dir (optionally scoped to diff) for hallucinated imports/APIs."""
    root = Path(target).resolve()
    diff_files = parse_diff_files(diff_text, root) if diff_text else None
    sites = collect_imports(root, diff_files)
    findings: list[dict] = []
    seen: set[tuple] = set()

    for s in sites:
        if s.language == "python" and s.package in _STDLIB:
            continue
        if s.language == "node" and (s.package in _NODE_BUILTINS or s.package.startswith("node:")):
            continue
        if _is_internal(s.package, s.language, root):
            continue
        key = (s.package, s.language)
        if key in seen:
            continue
        seen.add(key)

        exists = registry_exists(s.package, s.language)
        squat = typosquat_of(s.package, s.language)
        first_use = f"{s.file}:{s.line}"

        if exists is False and (s.guarded or s.typecheck):
            # Optional dep behind try/except ImportError (py2/3 shims,
            # platform-specific wheels) or under `if TYPE_CHECKING:`.
            # Real-but-uninstallable or never-executed — informational
            # only, never a BLOCK.
            findings.append({
                "id": f"HALLU-{len(findings) + 1:02d}",
                "scanner": "hallucination",
                "severity": 2,
                "file": s.file, "line": s.line,
                "package": s.package,
                "verdict": "guarded_optional" if s.guarded else "typecheck_only",
                "message": f"ℹ️ Optional import `{s.package}` "
                           + ("guarded by try/except ImportError" if s.guarded
                              else "under `if TYPE_CHECKING:` (never runs at runtime)")
                           + " — absent from registry but tolerated.",
                "fix": "No action unless the guarded path is load-bearing — "
                       "then pin the real dependency.",
            })
        elif exists is False:
            findings.append({
                "id": f"HALLU-{len(findings) + 1:02d}",
                "scanner": "hallucination",
                "severity": 10,
                "file": s.file, "line": s.line,
                "package": s.package,
                "verdict": "hallucinated",
                "message": f"\U0001f534 {RED_FLAG} `{s.package}` "
                           f"does not exist on {'PyPI' if s.language == 'python' else 'npm'} "
                           f"(first use {first_use}).",
                "fix": f"Remove the import or replace with a real library. "
                       f"Verify at pypi.org / npmjs.com before re-adding.",
            })
        elif exists is None:
            findings.append({
                "id": f"HALLU-{len(findings) + 1:02d}",
                "scanner": "hallucination",
                "severity": 4,
                "file": s.file, "line": s.line,
                "package": s.package,
                "verdict": "unknown_offline",
                "message": f"\U0001f7e1 Unverified import `{s.package}` "
                           f"(registry unreachable — could not confirm).",
                "fix": "Re-run with network access to confirm this package exists.",
            })
        if squat:
            findings.append({
                "id": f"HALLU-{len(findings) + 1:02d}",
                "scanner": "hallucination",
                "severity": 8,
                "file": s.file, "line": s.line,
                "package": s.package,
                "verdict": "possible_typosquat",
                "message": f"\U0001f6a8 Possible typosquat: `{s.package}` "
                           f"looks like `{squat}`. Classic slop-squatting vector.",
                "fix": f"Did you mean `{squat}`? Pin the exact version.",
            })

    # hallucinated-method pass (Python, installed packages only).
    # WARN-level by design: version skew between the scanned repo and the
    # locally installed package can cause false alarms.
    for s in { (x.file, x.package) for x in sites if x.language == "python" }:
        for attr, lineno in hallucinated_attrs(s[0], s[1]):
            findings.append({
                "id": f"HALLU-{len(findings) + 1:02d}",
                "scanner": "hallucination",
                "severity": 7,
                "file": s[0], "line": lineno,
                "package": f"{s[1]}.{attr}",
                "verdict": "possible_hallucinated_api",
                "message": f"\U0001f6a8 Possible hallucinated API: `{s[1]}.{attr}` "
                           f"not found in the installed `{s[1]}` — verify against "
                           f"the docs (may also be version skew).",
                "fix": f"Check the `{s[1]}` changelog/docs for `{attr}`.",
            })
    return findings
