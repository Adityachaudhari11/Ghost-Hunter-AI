"""Subagent B: CodeAgent — inspect test source for async/state issues."""

from __future__ import annotations

import re

_MISSING_AWAIT = re.compile(r"(?<!await\s)(\w+Service|\w+Repo|\w+Client)\.(\w+)\(", re.M)
_HARDCODED_TIMEOUT = re.compile(r"setTimeout\s*\(\s*[^,]+,\s*\d+\s*\)", re.M)
_SHARED_MUTABLE = re.compile(r"^(let|var)\s+\w+\s*=", re.M)
_GLOBAL_STATE = re.compile(r"\b(global|globalThis|window\.)\w+\s*=", re.M)


class CodeSignal:
    def __init__(self) -> None:
        self.missing_awaits: list[tuple[int, str]] = []
        self.hardcoded_timeouts: list[tuple[int, str]] = []
        self.shared_mutable_state: list[tuple[int, str]] = []

    def to_dict(self) -> dict:
        return {
            "missing_awaits": [(l, s) for l, s in self.missing_awaits[:3]],
            "hardcoded_timeouts": [(l, s) for l, s in self.hardcoded_timeouts[:3]],
            "shared_mutable_state": [(l, s) for l, s in self.shared_mutable_state[:3]],
        }


async def run(source: str, file: str = "") -> CodeSignal:
    """Scan test file source for async/state code issues."""
    sig = CodeSignal()
    lines = source.splitlines()
    for i, line in enumerate(lines, 1):
        if _MISSING_AWAIT.search(line) and "await" not in line and "async" in source:
            sig.missing_awaits.append((i, line.strip()[:120]))
        if _HARDCODED_TIMEOUT.search(line):
            sig.hardcoded_timeouts.append((i, line.strip()[:120]))
        if _SHARED_MUTABLE.match(line.strip()) or _GLOBAL_STATE.search(line):
            sig.shared_mutable_state.append((i, line.strip()[:120]))
    return sig
