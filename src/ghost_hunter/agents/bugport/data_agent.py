"""Subagent B: DataAgent — generate SQL fixture from snapshot DB query results."""

from __future__ import annotations

import json

from ...schemas.bugport import BugSnapshot

_PII_COLUMN_HINTS = {"email", "phone", "name", "address", "ssn", "dob", "ip"}


def _mask_value(col: str, val: object) -> str:
    """Replace PII column values with type-appropriate placeholders."""
    if any(pii in col.lower() for pii in _PII_COLUMN_HINTS):
        if isinstance(val, str):
            return "'<MASKED_STRING>'"
        if isinstance(val, int):
            return "0"
    if isinstance(val, str):
        return f"'{val}'"
    if val is None:
        return "NULL"
    return str(val)


def generate_sql_fixture(snapshot: BugSnapshot) -> str:
    """Produce INSERT SQL to seed the exact DB rows involved in the bug."""
    if not snapshot.db_query_results:
        return "-- No DB query results in snapshot"
    lines = [
        "-- BugPort SQL fixture",
        f"-- Snapshot: {snapshot.snapshot_id}",
        "-- Run in your local bugport_repro database",
        "",
    ]
    for i, row in enumerate(snapshot.db_query_results[:10]):
        if not isinstance(row, dict):
            continue
        table = row.pop("__table__", f"bugport_table_{i}")
        cols = list(row.keys())
        vals = [_mask_value(c, row[c]) for c in cols]
        lines.append(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
        )
    return "\n".join(lines)


async def run(snapshot: BugSnapshot) -> str:
    """Return SQL fixture string."""
    return generate_sql_fixture(snapshot)
