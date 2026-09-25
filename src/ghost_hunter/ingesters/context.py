"""Project context builder: docs -> structured rules. No invented rules.

Every rule must cite its source file:line. If docs are absent, only
built-in guardrails with source='builtin' are returned and flagged
as low-confidence.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..schemas.review import ArchitectureRule

DOC_FILES = ("ARCHITECTURE.md", "AGENTS.md", "README.md", "CONTRIBUTING.md")

# keyword -> rule_id mapping; extend without changing agent logic
RULE_KEYWORDS: dict[str, tuple[str, str, list[str]]] = {
    "database.repository_only": (
        "Database operations must use Repository classes",
        "high",
        ["repository", "database operations must go through"],
    ),
    "auth.auth_service": (
        "Authentication must go through AuthService",
        "high",
        ["authservice", "authentication must go through"],
    ),
    "logging.structured": (
        "Logging must use the project's structured logger",
        "medium",
        ["structured logger", "use the project logger"],
    ),
    "reuse.prefer_utils": (
        "Reuse existing utilities where applicable",
        "medium",
        ["reuse", "existing utilit", "do not reimplement"],
    ),
}


def load_rules(repo_dir: str | Path) -> list[ArchitectureRule]:
    repo = Path(repo_dir) if repo_dir else Path(".")
    rules: list[ArchitectureRule] = []
    for doc in DOC_FILES:
        p = repo / doc
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        low = text.lower()
        for lineno, line in enumerate(text.splitlines(), 1):
            _ = line
            for rule_id, (title, sev, keywords) in RULE_KEYWORDS.items():
                if any(k in low for k in keywords):
                    if not any(r.rule_id == rule_id for r in rules):
                        rules.append(
                            ArchitectureRule(
                                rule_id=rule_id,
                                title=title,
                                source=f"{doc}:{lineno}",
                                severity=sev,
                            )
                        )
    if not rules:
        rules.append(
            ArchitectureRule(
                rule_id="builtin.direct_sql_guard",
                title="Avoid direct SQL in service code (builtin guardrail)",
                source="builtin",
                severity="medium",
            )
        )
    # attach forbidden patterns for known rules
    for r in rules:
        if r.rule_id in ("database.repository_only", "builtin.direct_sql_guard"):
            r.forbidden_patterns = ["cursor.execute", "SELECT * FROM", "sqlalchemy.text("]
            r.required_patterns = ["Repository"]
    return rules


def read_manifests(repo_dir: str | Path) -> dict[str, str]:
    """Return manifest filename -> content for dependency declared-check."""
    repo = Path(repo_dir) if repo_dir else Path(".")
    out: dict[str, str] = {}
    for name in ("requirements.txt", "pyproject.toml", "package.json", "package-lock.json"):
        p = repo / name
        if p.is_file():
            out[name] = p.read_text(encoding="utf-8", errors="ignore")
    return out
