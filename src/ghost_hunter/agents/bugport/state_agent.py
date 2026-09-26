"""Subagent C: StateAgent — initialize in-memory objects to production state.

Uses Laya Noul to determine which state fields are PII-sensitive before
including them in the reproduction harness.
"""

from __future__ import annotations

from ...laya.client import laya
from ...schemas.bugport import BugSnapshot


async def run(snapshot: BugSnapshot) -> tuple[str, list[str]]:
    """Return (state_init_code, relevant_fields).

    relevant_fields is the subset of state_snapshot keys that Laya
    classifies as bug-relevant (not PII, not unrelated).
    """
    relevant: list[str] = []
    for key in snapshot.state_snapshot:
        ctx = {"field": key, "value_type": type(snapshot.state_snapshot[key]).__name__}
        # PII gate
        pii_result = await laya.noul("Does this field contain PII or sensitive personal data?", ctx)
        if pii_result.value:
            continue
        relevant.append(key)
    code = _generate_state_code(snapshot, relevant)
    return code, relevant


def _generate_state_code(snapshot: BugSnapshot, fields: list[str]) -> str:
    """Produce Python code to reconstruct the in-memory state."""
    lines = [
        "# BugPort StateAgent — in-memory state reconstruction",
        f"# Snapshot: {snapshot.snapshot_id}",
        "",
        "def bugport_init_state():",
        '    """Reconstruct production state for local reproduction."""',
    ]
    if not fields:
        lines.append("    return {}  # No relevant state fields identified")
    else:
        lines.append("    return {")
        for f in fields:
            val = snapshot.state_snapshot.get(f)
            lines.append(f"        {f!r}: {val!r},")
        lines.append("    }")
    return "\n".join(lines)
