"""Dependency / API hallucination detector (Module A1).

Deterministic: parse new imports from diff, check declared manifests,
verify against real registries (injectable checker for offline tests).
Wording: 'unverified dependency / possible hallucination', never 'malicious'.
"""

from __future__ import annotations

import sys
from typing import Awaitable, Callable

import httpx

from ...schemas.common import Evidence, Finding, Severity
from ...ingesters.diff import (
    extract_new_imports,
    resolve_js_package,
    resolve_python_package,
)
from ...schemas.review import ChangedFile

Checker = Callable[[str, str], Awaitable[bool]]  # (ecosystem, package) -> exists?

# Never treat the standard library as an external dependency.
STDLIB: set[str] = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

PY_EXT = (".py",)
JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


async def _pypi_exists(package: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://pypi.org/pypi/{package}/json")
            return r.status_code == 200
    except Exception:
        return False  # network failure -> unverifiable, handled by caller


async def _npm_exists(package: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://registry.npmjs.org/{package}")
            return r.status_code == 200
    except Exception:
        return False


def _declared(package: str, manifests: dict[str, str]) -> bool:
    for content in manifests.values():
        if package in content:
            return True
    return False


def _ecosystem(path: str) -> str:
    if path.endswith((".py", ".txt", ".toml")):
        return "pypi"
    return "npm"


async def run(
    files: list[ChangedFile],
    manifests: dict[str, str] | None = None,
    checker: Checker | None = None,
    known_local: set[str] | None = None,
) -> list[Finding]:
    """known_local: first-party top-level module names (never external)."""
    manifests = manifests or {}
    known_local = known_local or set()
    findings: list[Finding] = []
    new_imports = extract_new_imports(files)
    for f in files:
        # Only lines shaped like real import statements. This kills noise from
        # string literals that merely mention the word "import".
        wanted = set(new_imports.get(f.path, []))
        if not wanted:
            continue
        is_py = f.path.endswith(PY_EXT)
        is_js = f.path.endswith(JS_EXT)
        if not (is_py or is_js):
            continue  # manifests/locks/docs are declarations, not imports
        for lineno, text in f.added_lines:
            stripped = text.strip()
            if stripped not in wanted:
                continue
            pkg = ""
            eco = ""
            if is_py and stripped.startswith(("import ", "from ")):
                pkg = resolve_python_package(stripped)
                eco = "pypi"
            elif is_js and ("import" in stripped or "require" in stripped or stripped.startswith("export")):
                pkg = resolve_js_package(stripped)
                eco = "npm"
            if not pkg:
                continue
            if pkg in STDLIB or pkg in known_local:
                continue
            if pkg.startswith(("@/", "#", "~")):
                continue  # path aliases / locals, not registry packages
            # only flag packages introduced in added lines that look external
            declared = _declared(pkg, manifests)
            exists: bool | None
            if checker is not None:
                exists = await checker(eco, pkg)
            else:
                exists = await (_pypi_exists(pkg) if eco == "pypi" else _npm_exists(pkg))
            if exists is False:
                findings.append(
                    Finding(
                        finding_id="GH-000",
                        source="dependency_agent",
                        module="dependency",
                        severity=Severity.CRITICAL,
                        confidence=0.9,
                        file=f.path,
                        line=lineno,
                        rule=f"{eco}:{pkg}",
                        observed=f"Unverified dependency '{pkg}' ({eco}); possible package hallucination",
                        evidence=[
                            Evidence(kind="registry_lookup", description=f"{eco} registry lookup", ref=f"{eco}:{pkg}", data={"exists": False}),
                            Evidence(kind="code_location", description="New import in diff", ref=f"{f.path}:{lineno}", data={"import": stripped}),
                            Evidence(kind="manifest_check", description="Declared in project manifests?", ref="manifests", data={"declared": declared}),
                        ],
                        suggestion=f"Verify '{pkg}' exists in {eco}; if real, add to manifests; else remove/replace.",
                        uncertainty="Network failure also yields not-found; re-check with network before blocking.",
                    )
                )
            elif not declared and exists:
                findings.append(
                    Finding(
                        finding_id="GH-000",
                        source="dependency_agent",
                        module="dependency",
                        severity=Severity.MEDIUM,
                        confidence=0.7,
                        file=f.path,
                        line=lineno,
                        rule=f"{eco}:{pkg}",
                        observed=f"New dependency '{pkg}' not declared in project manifests",
                        evidence=[
                            Evidence(kind="registry_lookup", description="Registry exists", ref=f"{eco}:{pkg}", data={"exists": True}),
                            Evidence(kind="manifest_check", description="Missing from manifests", ref=f"{f.path}:{lineno}", data={"declared": False}),
                        ],
                        suggestion="Add to requirements/package.json or remove if unneeded.",
                    )
                )
    # dedupe by (file, package)
    seen: set[tuple[str, str]] = set()
    uniq: list[Finding] = []
    for fd in findings:
        key = (fd.file, fd.rule)
        if key not in seen:
            seen.add(key)
            uniq.append(fd)
    return uniq
