"""Subagent A: MutationRunner — generates/runs mutation tests on PR diff.

Calls the configured mutation runner (stub | mutmut | cosmic-ray).
Returns a list of MutantResult objects (killed + survived).
"""

from __future__ import annotations

from ...ingesters.mutation import generate_mutants_for_diff
from ...schemas.mutaci import MutantResult


async def run(diff_text: str, runner: str = "stub") -> list[MutantResult]:
    """Scope mutation testing to the PR diff.  Returns all mutant results."""
    return generate_mutants_for_diff(diff_text, runner)
