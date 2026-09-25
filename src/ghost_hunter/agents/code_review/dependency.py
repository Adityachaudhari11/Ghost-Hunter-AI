"""Dependency / API hallucination detector (Module A1).

Deterministic: parse new imports from diff, check declared manifests,
verify against real registries (injectable checker for offline tests).
Wording: 'unverified dependency / possible hallucination', never 'malicious'.
"""

from __future__ import annotations

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
) -> list[Finding]:
    manifests = manifests or {}
    findings: list[Finding] = []
    new_imports = extract_new_imports(files)
    for f in files:
        for _, text in f.added_lines:
            pkg = ""
            eco = _ecosystem(f.path)
            if f.path.endswith(".py") or ".py" in f.path or eco == "pypi":
                if text.strip().startswith(("import ", "from ")):
                    pkg = resolve_python_package(text.strip())
                    eco = "pypi"
            if not pkg and ("import" in text or "require" in text):
                pkg = resolve_js_package(text)
                if pkg:
                    eco = "npm"
            if not pkg:
                continue
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
                        line=0,
                        rule=f"{eco}:{pkg}",
                        observed=f"Unverified dependency '{pkg}' ({eco}); possible package hallucination",
                        evidence=[
                            Evidence(kind="registry_lookup", description=f"{eco} registry lookup", ref=f"{eco}:{pkg}", data={"exists": False}),
                            Evidence(kind="code_location", description="New import in diff", ref=f.path, data={"import": text.strip()}),
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
                        line=0,
                        rule=f"{eco}:{pkg}",
                        observed=f"New dependency '{pkg}' not declared in project manifests",
                        evidence=[
                            Evidence(kind="registry_lookup", description="Registry exists", ref=f"{eco}:{pkg}", data={"exists": True}),
                            Evidence(kind="manifest_check", description="Missing from manifests", ref="manifests", data={"declared": False}),
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
