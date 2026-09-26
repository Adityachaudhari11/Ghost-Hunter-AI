"""
FlakeHunter — Fix Generator.

Given a FlakeClassification and the original test file content,
generates a patched version of the test that eliminates the flake.
Uses Claude (via Anthropic API) for precise edits, with a demo fallback.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .classifier import FlakeClassification


@dataclass
class FlakeFix:
    original_test: str
    patched_test: str
    description: str
    category: str
    diff_lines: list[str]   # unified diff lines for display


# Demo patches keyed by category — applied when no Anthropic client is available
DEMO_PATCHES: dict[str, dict] = {
    "async": {
        "pattern": r"setTimeout\(\s*(?:resolve|done)\s*,\s*(\d+)\)",
        "replacement": "await vi.waitFor(() => expect(condition).toBe(true), { timeout: 5000 })",
        "description": "Replaced hardcoded setTimeout with waitFor polling",
    },
    "state": {
        "pattern": r"(beforeAll\s*\()",
        "replacement": "beforeEach(",
        "description": "Moved shared setup from beforeAll to beforeEach to prevent state contamination",
    },
    "ordering": {
        "pattern": r"(it\s*\(['\"])([^'\"]+)(['\"])",
        "replacement": r'\1[standalone] \2\3',
        "description": "Marked test as standalone; add explicit precondition setup in beforeEach",
    },
    "environment": {
        "pattern": r"(fetch|axios\.get|http\.get)\s*\(\s*['\"]([^'\"]+)['\"]",
        "replacement": r"mockFetch('\2'",
        "description": "Replaced real network call with mockFetch to eliminate environment dependency",
    },
    "resource": {
        "pattern": r"(describe|it)\s*\(",
        "replacement": r"\1.concurrent(",
        "description": "Added .concurrent to allow parallel execution with resource limits",
    },
}


def generate_fix(
    classification: FlakeClassification,
    test_content: str,
    test_file_path: str,
    client=None,  # Anthropic client
) -> FlakeFix:
    """
    Generate a patched test file that eliminates the flake.
    Uses Claude if available, otherwise applies a demo patch.
    """
    if client is not None:
        return _generate_with_claude(classification, test_content, test_file_path, client)
    return _apply_demo_patch(classification, test_content, test_file_path)


def _generate_with_claude(
    classification: FlakeClassification,
    test_content: str,
    test_file_path: str,
    client,
) -> FlakeFix:
    """Use Claude to generate a precise fix for the flaky test."""
    prompt = f"""You are fixing a flaky test. Root cause: {classification.category}.

Reasoning: {classification.reasoning}

Fix template to apply:
{classification.fix_template}

Original test file ({test_file_path}):
```typescript
{test_content}
```

Return ONLY the complete fixed TypeScript test file, no explanation.
Make the minimal change that eliminates the flake for the '{classification.category}' root cause."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    patched = response.content[0].text.strip()
    # Strip markdown code fences if present
    if patched.startswith("```"):
        patched = re.sub(r"^```[a-z]*\n?", "", patched)
        patched = re.sub(r"\n?```$", "", patched)

    return FlakeFix(
        original_test=test_content,
        patched_test=patched,
        description=f"[Claude] Fixed {classification.category} flake: {classification.reasoning.split(chr(10))[0]}",
        category=classification.category,
        diff_lines=_make_diff(test_content, patched, test_file_path),
    )


def _apply_demo_patch(
    classification: FlakeClassification,
    test_content: str,
    test_file_path: str,
) -> FlakeFix:
    """Apply a regex-based demo patch for the given category."""
    patch_info = DEMO_PATCHES.get(classification.category, DEMO_PATCHES["async"])
    patched = re.sub(
        patch_info["pattern"],
        patch_info["replacement"],
        test_content,
        count=1,
    )
    return FlakeFix(
        original_test=test_content,
        patched_test=patched,
        description=f"[Demo] {patch_info['description']}",
        category=classification.category,
        diff_lines=_make_diff(test_content, patched, test_file_path),
    )


def _make_diff(original: str, patched: str, filepath: str) -> list[str]:
    """Generate a simple unified diff for display."""
    orig_lines = original.splitlines()
    patch_lines = patched.splitlines()
    diff = [f"--- a/{filepath}", f"+++ b/{filepath}"]
    for i, (o, p) in enumerate(zip(orig_lines, patch_lines)):
        if o != p:
            diff.append(f"@@ line {i + 1} @@")
            diff.append(f"-  {o}")
            diff.append(f"+  {p}")
    if len(patch_lines) > len(orig_lines):
        for line in patch_lines[len(orig_lines):]:
            diff.append(f"+  {line}")
    return diff
