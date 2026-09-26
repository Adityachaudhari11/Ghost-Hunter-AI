"""FlakeHunter fix generator — deterministic fix per root cause class.

One fix template per root cause, applied to the test source.
No LLM; all transformations are deterministic regex replacements.
"""

from __future__ import annotations

import re

from ...schemas.flakehunter import FlakeRootCause

# Fix templates: (description, pattern, replacement)
_FIXES: dict[FlakeRootCause, tuple[str, str, str]] = {
    FlakeRootCause.ASYNC_TIMING: (
        "Replace hardcoded setTimeout/sleep with deterministic waitFor()",
        r"setTimeout\s*\(\s*([^,]+),\s*\d+\s*\)",
        r"await waitFor(() => \1)",
    ),
    FlakeRootCause.STATE_POLLUTION: (
        "Add afterEach cleanup to reset shared state",
        r"(describe\([^{]+\{)",
        r"\1\n  afterEach(() => { jest.clearAllMocks(); store.reset(); });",
    ),
    FlakeRootCause.PORT_COLLISION: (
        "Use dynamic port allocation instead of hardcoded port",
        r"listen\s*\(\s*(\d{4,5})\s*\)",
        r"listen(0)",  # OS assigns free port
    ),
    FlakeRootCause.TEST_ORDERING: (
        "Add explicit beforeEach setup to make test independent of ordering",
        r"(it\s*\(['\"])",
        r"beforeEach(() => { setup(); }); \1",
    ),
    FlakeRootCause.ENVIRONMENT: (
        "Add environment guard to skip test when required env is missing",
        r"^(it|test)\s*\(",
        r'(process.env.CI ? it.skip : it)(',
    ),
}


def generate_fix(root_cause: FlakeRootCause, source: str) -> tuple[str, str]:
    """Return (description, patched_source). Falls back to advisory if no match."""
    if root_cause not in _FIXES or root_cause == FlakeRootCause.UNKNOWN:
        desc = "Root cause unclassified — manual review required"
        return desc, source
    desc, pattern, replacement = _FIXES[root_cause]
    patched = re.sub(pattern, replacement, source, count=1)
    if patched == source:
        # Pattern didn't match — return advisory-only
        desc = f"{desc} (pattern not found — apply manually)"
    return desc, patched
