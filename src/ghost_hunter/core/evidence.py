"""Evidence Engine: gate every finding on evidence, assign stable IDs."""

from __future__ import annotations

import itertools

from ..schemas.common import Finding

_counter = itertools.count(1)


def reset_ids() -> None:
    global _counter
    _counter = itertools.count(1)


def assign_id(f: Finding) -> Finding:
    if not f.finding_id or f.finding_id == "GH-000":
        f.finding_id = f"GH-{next(_counter):03d}"
    return f


def validate_findings(findings: list[Finding]) -> list[Finding]:
    """Drop findings without evidence; keep audit trail in summary instead."""
    valid: list[Finding] = []
    for f in findings:
        if not f.evidence:
            continue  # AI must never invent evidence; no evidence -> no finding
        if not f.answers_six_questions():
            continue
        valid.append(assign_id(f))
    # deterministic order for reports / tests
    valid.sort(key=lambda x: (x.severity.value, x.file, x.line))
    return valid
