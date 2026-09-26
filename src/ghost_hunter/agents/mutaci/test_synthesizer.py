"""Subagent C: TestSynthesizer — generates test descriptions for real gaps.

For each BehavioralGap returned by GapClassifier, produces:
  - A plain-English test description (what to assert)
  - A pytest-compatible test stub

No LLM needed — derives tests deterministically from the mutation operator
and the surrounding code fragment.
"""

from __future__ import annotations

from ...schemas.mutaci import BehavioralGap

_TEST_TEMPLATES: dict[str, str] = {
    "ROR": (
        "def test_{fn_name}_boundary_condition():\n"
        "    # Derived from ROR mutant at {file}:{line}\n"
        "    # The condition '{original}' must NOT pass when '{mutated}' would\n"
        "    result = {fn_name}(boundary_value)\n"
        "    assert result  # verify exact boundary behavior"
    ),
    "AOR": (
        "def test_{fn_name}_arithmetic_correctness():\n"
        "    # Derived from AOR mutant at {file}:{line}\n"
        "    # Arithmetic must produce correct result; off-by-one not tolerated\n"
        "    assert {fn_name}(known_input) == expected_output"
    ),
    "LCR": (
        "def test_{fn_name}_logical_condition():\n"
        "    # Derived from LCR mutant at {file}:{line}\n"
        "    # Test both True and False branches of the logical condition\n"
        "    assert {fn_name}(true_case) == True\n"
        "    assert {fn_name}(false_case) == False"
    ),
    "UOI": (
        "def test_{fn_name}_negation_semantics():\n"
        "    # Derived from UOI mutant at {file}:{line}\n"
        "    # Removing 'not' would invert behavior — must have explicit assertion\n"
        "    assert not {fn_name}(negative_case)"
    ),
    "SBR": (
        "def test_{fn_name}_return_value():\n"
        "    # Derived from SBR mutant at {file}:{line}\n"
        "    # Return value semantics must be explicitly asserted\n"
        "    result = {fn_name}(input_causing_none_return)\n"
        "    assert result is None  # not False or empty"
    ),
}

_DEFAULT_TEMPLATE = (
    "def test_{fn_name}_behavioral_gap():\n"
    "    # Derived from {operator} mutant at {file}:{line}\n"
    "    # '{original}' was replaced with '{mutated}' without test failure\n"
    "    # Add assertion that explicitly covers this code path"
)


def _extract_fn_name(file: str, original: str) -> str:
    """Best-effort: extract function name from file path or code snippet."""
    import re
    # Try to find function name in original line
    m = re.search(r"\bdef\s+(\w+)|(\w+)\s*\(", original)
    if m:
        return m.group(1) or m.group(2) or "subject"
    # Fall back to file stem
    return file.split("/")[-1].replace(".py", "").replace("-", "_") or "subject"


async def run(gaps: list[BehavioralGap]) -> list[BehavioralGap]:
    """Populate suggested_test for each gap. Returns gaps with tests filled in."""
    enriched: list[BehavioralGap] = []
    for gap in gaps:
        template = _TEST_TEMPLATES.get(gap.description[:3], _DEFAULT_TEMPLATE)
        # Extract operator from description prefix (first 3 chars of description start)
        import re
        op_match = re.search(r"\b(ROR|AOR|LCR|UOI|SBR)\b", gap.description)
        operator = op_match.group(1) if op_match else "MUT"
        template = _TEST_TEMPLATES.get(operator, _DEFAULT_TEMPLATE)
        fn_name = _extract_fn_name(gap.file, gap.description)
        test_stub = template.format(
            fn_name=fn_name,
            file=gap.file,
            line=gap.line,
            operator=operator,
            original=gap.description[:60],
            mutated="[mutated form]",
        )
        enriched.append(
            BehavioralGap(
                mutant_id=gap.mutant_id,
                file=gap.file,
                line=gap.line,
                description=gap.description,
                impact_score=gap.impact_score,
                suggested_test=test_stub,
            )
        )
    return enriched
