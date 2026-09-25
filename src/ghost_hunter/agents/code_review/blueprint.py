"""Blueprint / architecture auditor (Module A2).

Only flags rules that cite a source. Forbidden-pattern match on added lines.
No LLM invention: if rules come from docs, cite doc:line; builtin guard
is marked source='builtin' with lower confidence.
"""

from __future__ import annotations

from ...schemas.common import Evidence, Finding, Severity
from ...schemas.review import ArchitectureRule, ChangedFile

# rule_id -> (patterns, expected)
PATTERNS: dict[str, tuple[list[str], str]] = {
    "database.repository_only": (["cursor.execute", "SELECT * FROM", "SELECT ", "sqlalchemy.text("], "UserRepository / Repository layer"),
    "builtin.direct_sql_guard": (["cursor.execute", "SELECT * FROM", "sqlalchemy.text("], "Repository layer"),
    "auth.auth_service": (["jwt.decode(", "request.headers.get('Authorization')"], "AuthService"),
    "logging.structured": (["print("], "structured logger"),
}


async def run(files: list[ChangedFile], rules: list[ArchitectureRule]) -> list[Finding]:
    out: list[Finding] = []
    for f in files:
        added = "\n".join(t for _, t in f.added_lines)
        lineno = f.added_lines[0][0] if f.added_lines else 0
        for rule in rules:
            pats, expected = PATTERNS.get(rule.rule_id, ([], ""))
            if not pats:
                # generic: match forbidden_patterns attached by context loader
                pats = rule.forbidden_patterns
                expected = ", ".join(rule.required_patterns) or "project layer"
            for pat in pats:
                if pat and pat in added:
                    builtin = rule.source == "builtin"
                    out.append(
                        Finding(
                            finding_id="GH-000",
                            source="blueprint_agent",
                            module="blueprint",
                            severity=Severity.HIGH if rule.severity == "high" else Severity.MEDIUM,
                            confidence=0.6 if builtin else 0.85,
                            file=f.path,
                            line=lineno,
                            rule=rule.rule_id,
                            observed=f"Possible architecture violation: '{pat}' found; expected {expected}",
                            evidence=[
                                Evidence(kind="rule_citation", description=rule.title, ref=rule.source),
                                Evidence(kind="code_location", description="Matched pattern in added lines", ref=f"{f.path}:{lineno}", data={"pattern": pat}),
                            ],
                            suggestion=f"Route via {expected} per {rule.source}.",
                            uncertainty="Builtin guardrail" if builtin else "",
                        )
                    )
                    break
    return out
