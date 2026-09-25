"""Blueprint / architecture auditor (Module A2).

Only flags rules that cite a source. Forbidden-pattern match on added lines.
No LLM invention: if rules come from docs, cite doc:line; builtin guard
is marked source='builtin' with lower confidence.
"""

from __future__ import annotations

import io
import re
import tokenize

from ...core.logging import get_logger
from ...schemas.common import Evidence, Finding, Severity
from ...schemas.review import ArchitectureRule, ChangedFile

log = get_logger("blueprint_agent")

# rule_id -> (patterns, expected)
PATTERNS: dict[str, tuple[list[str], str]] = {
    "database.repository_only": (["cursor.execute", "SELECT * FROM", "SELECT ", "sqlalchemy.text("], "UserRepository / Repository layer"),
    "builtin.direct_sql_guard": (["cursor.execute", "SELECT * FROM", "sqlalchemy.text("], "Repository layer"),
    "auth.auth_service": (["jwt.decode(", "request.headers.get('Authorization')"], "AuthService"),
    "logging.structured": (["print("], "structured logger"),
}


_STR_RE = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
_PROSE_EXT = (".md", ".rst", ".txt")


def _code_only(text: str) -> str:
    """Remove string-literal contents and comments so patterns inside docs,
    pattern tables, or comments do not match. Real calls like
    cursor.execute("...") keep their code part and still match."""
    no_strings = _STR_RE.sub('""', text)
    no_strings = re.sub(r"#.*$", "", no_strings)  # py/sh comments
    return re.sub(r"//.*$", "", no_strings)  # js/ts comments


def _string_spans(source: str) -> dict[int, list[tuple[int, int]]]:
    """Line -> string-literal column spans via tokenize (handles docstrings)."""
    spans: dict[int, list[tuple[int, int]]] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.STRING:
                continue
            (sl, sc), (el, ec) = tok.start, tok.end
            for ln in range(sl, el + 1):
                s = sc if ln == sl else 0
                e = ec if ln == el else 10**9
                spans.setdefault(ln, []).append((s, e))
    except (tokenize.TokenError, SyntaxError, IndentationError) as e:
        log.debug("string-span tokenize fallback: %s", type(e).__name__)
    return spans


def _match_in_code(line: str, pat: str, spans: list[tuple[int, int]]) -> bool:
    """True if pat occurs on line outside string-literal spans."""
    start = 0
    while True:
        i = line.find(pat, start)
        if i < 0:
            return False
        j = i + len(pat)
        if not any(s < j and i < e for s, e in spans):
            return True
        start = j


async def run(
    files: list[ChangedFile],
    rules: list[ArchitectureRule],
    full_sources: dict[str, str] | None = None,
) -> list[Finding]:
    """full_sources enables tokenizer-precise matching for .py (docstring-safe)."""
    full_sources = full_sources or {}
    span_cache: dict[str, dict[int, list[tuple[int, int]]]] = {}
    out: list[Finding] = []
    for f in files:
        if f.path.endswith(_PROSE_EXT):
            continue  # prose mentions of a pattern are not code violations
        spans: dict[int, list[tuple[int, int]]] = {}
        if f.path.endswith(".py") and f.path in full_sources:
            if f.path not in span_cache:
                span_cache[f.path] = _string_spans(full_sources[f.path])
            spans = span_cache[f.path]
        for rule in rules:
            pats, expected = PATTERNS.get(rule.rule_id, ([], ""))
            if not pats:
                # generic: match forbidden_patterns attached by context loader
                pats = rule.forbidden_patterns
                expected = ", ".join(rule.required_patterns) or "project layer"
            hit: tuple[int, str, str] | None = None  # (lineno, pattern, snippet)
            for lineno, text in f.added_lines:
                if spans:
                    line_spans = spans.get(lineno, [])
                    for pat in pats:
                        if pat and _match_in_code(text, pat, line_spans):
                            hit = (lineno, pat, text.strip())
                            break
                else:
                    code = _code_only(text)
                    for pat in pats:
                        if pat and pat in code:
                            hit = (lineno, pat, text.strip())
                            break
                if hit:
                    break
            if hit:
                lineno, pat, snippet = hit
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
                            Evidence(kind="code_location", description="Matched pattern in added lines", ref=f"{f.path}:{lineno}", data={"pattern": pat, "snippet": snippet[:300]}),
                        ],
                        suggestion=f"Route via {expected} per {rule.source}.",
                        uncertainty="Builtin guardrail" if builtin else "",
                    )
                )
    return out
