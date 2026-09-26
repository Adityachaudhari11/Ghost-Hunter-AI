"""MutaCI ingester — scope mutation generation to PR diff lines only.

Reads a unified diff and produces:
  - A list of (file, lineno, source_fragment) tuples for each added line
  - Generates synthetic mutants for demo/stub mode (no external runner needed)
"""

from __future__ import annotations

import re
import uuid

from ..ingesters.diff import parse_diff
from ..schemas.mutaci import MutantResult

# Simple mutation operators applied to changed source lines
# Patterns use non-word-boundary aware lookbehind/lookahead for symbols
_OPERATORS: list[tuple[str, str, str]] = [
    ("AOR", r"(?<![=!<>+\-*/])(\+)(?!=)",  "-"),  # arithmetic: + -> -
    ("AOR", r"(?<![=!<>+\-*/])(-)(?!=)",   "+"),  # arithmetic: - -> +
    ("ROR", r"==",                          "!="),  # relational: == -> !=
    ("ROR", r"!=",                          "=="),  # relational: != -> ==
    ("ROR", r"<=",                          "<"),   # relational: <= -> <
    ("ROR", r">=",                          ">"),   # relational: >= -> >
    ("ROR", r"(?<![=!<>])>(?!=)",           "<"),   # relational: > -> <
    ("ROR", r"(?<![=!<>])<(?!=)",           ">"),   # relational: < -> >
    ("LCR", r"\band\b",                     "or"),  # logical: and -> or
    ("LCR", r"\bor\b",                      "and"), # logical: or -> and
    ("UOI", r"\bnot\s+",                    ""),    # unary: not removal
    ("SBR", r"\breturn\s+None\b",           "return False"),  # None -> False
    ("SBR", r"\breturn\s+False\b",          "return None"),   # False -> None
    ("SBR", r"\breturn\s+True\b",           "return False"),  # True -> False
]


def generate_mutants_for_diff(diff_text: str, runner: str = "stub") -> list[MutantResult]:
    """Scope mutants to the exact lines changed in the PR diff.

    In stub mode (default for demo), generates mutants deterministically
    without executing a real mutation framework.
    """
    files = parse_diff(diff_text)
    results: list[MutantResult] = []

    for f in files:
        if not f.path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            continue
        for lineno, text in f.added_lines:
            for op_name, pattern, replacement in _OPERATORS:
                m = re.search(pattern, text)
                if not m:
                    continue
                mutated = re.sub(pattern, replacement, text, count=1)
                if mutated == text:
                    continue
                # In stub mode: heuristically decide if mutant is "killed"
                # (killed = test covers this operator; survived = gap)
                killed = _stub_killed(text, op_name)
                results.append(
                    MutantResult(
                        mutant_id=f"mut-{uuid.uuid4().hex[:6]}",
                        file=f.path,
                        line=lineno,
                        operator=op_name,
                        original=text.strip(),
                        mutated=mutated.strip(),
                        killed=killed,
                    )
                )
    return results


def _stub_killed(line: str, operator: str) -> bool:
    """Stub heuristic: if the changed line has an assert/test/check nearby,
    treat the mutant as killed. Otherwise it survives (= gap found)."""
    low = line.lower()
    # Lines with assertions or obvious test constructs likely covered
    if any(k in low for k in ("assert", "test_", "expect(", "should", "==", "!=")):
        return True
    # Arithmetic on pure assignments with no assertion -> likely survives
    if operator in ("AOR", "UOI") and "=" in line and "==" not in line:
        return False
    return True  # default: assume killed (conservative)
