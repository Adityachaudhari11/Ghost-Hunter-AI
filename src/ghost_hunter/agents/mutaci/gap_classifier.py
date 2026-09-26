"""Subagent B: GapClassifier — uses Laya Score to rank surviving mutants.

For each surviving mutant:
  - Asks Laya: "How impactful is this behavioral gap? (1-10)"
  - Filters out noise (score < 5); keeps real gaps
  - Returns ranked list ready for test synthesis
"""

from __future__ import annotations

from ...laya.client import laya
from ...schemas.mutaci import BehavioralGap, MutantResult

_GAP_THRESHOLD = 5.0  # Only gaps scoring >= this are considered real


def _describe_mutant(m: MutantResult) -> str:
    return (
        f"File: {m.file}, line {m.line}. "
        f"Operator: {m.operator}. "
        f"Original: '{m.original}' → Mutated: '{m.mutated}'. "
        f"The test suite did NOT catch this change."
    )


async def run(survivors: list[MutantResult]) -> list[BehavioralGap]:
    """Score surviving mutants; return only real behavioral gaps."""
    gaps: list[BehavioralGap] = []
    for m in survivors:
        if m.killed:
            continue
        ctx = _describe_mutant(m)
        result = await laya.score(
            "How impactful is this behavioral gap on production correctness?",
            ctx,
            scale=(1, 10),
        )
        score = float(result.value)
        if score < _GAP_THRESHOLD:
            continue
        description = _plain_english(m)
        gaps.append(
            BehavioralGap(
                mutant_id=m.mutant_id,
                file=m.file,
                line=m.line,
                description=description,
                impact_score=score,
                suggested_test="",  # filled by TestSynthesizer
            )
        )
    # Sort by impact score descending
    gaps.sort(key=lambda g: g.impact_score, reverse=True)
    return gaps


def _plain_english(m: MutantResult) -> str:
    """Convert a mutant into a developer-readable description."""
    op_descriptions = {
        "ROR": f"The condition '{m.original}' could behave as '{m.mutated}' if the comparison operator is wrong",
        "AOR": f"The arithmetic in '{m.original}' could be '{m.mutated}' — arithmetic off-by-one not caught by tests",
        "LCR": f"The logical condition '{m.original}' passes when '{m.mutated}' is used — boolean logic untested",
        "UOI": f"Removing 'not' from '{m.original}' inverts the condition — negation not covered by tests",
        "SBR": f"Return value '{m.original}' was replaced with '{m.mutated}' without test failure — return semantics untested",
    }
    return op_descriptions.get(
        m.operator,
        f"Mutation in '{m.original}' (→ '{m.mutated}') at {m.file}:{m.line} survived all tests",
    )
