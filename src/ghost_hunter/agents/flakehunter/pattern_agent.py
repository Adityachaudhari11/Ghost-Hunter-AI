"""Subagent A: PatternAgent — analyse CI run logs for timing/failure patterns."""

from __future__ import annotations

import re

from ...schemas.flakehunter import CIRunLog


_TIMING_PATTERNS = [
    re.compile(r"timeout", re.I),
    re.compile(r"timed? out", re.I),
    re.compile(r"after\s+\d+\s*m?s", re.I),
    re.compile(r"settimeout|sleep|delay|waitfor", re.I),
]
_STATE_PATTERNS = [
    re.compile(r"stale\s+state|store\s+not\s+reset|pollution", re.I),
    re.compile(r"globalState|sharedState|authStore", re.I),
]
_PORT_PATTERNS = [
    re.compile(r"EADDRINUSE|address already in use|port \d+ in use", re.I),
]


class PatternSignal:
    def __init__(self) -> None:
        self.timing_hits: int = 0
        self.state_hits: int = 0
        self.port_hits: int = 0
        self.raw_patterns: list[str] = []

    def to_dict(self) -> dict:
        return {
            "timing_hits": self.timing_hits,
            "state_hits": self.state_hits,
            "port_hits": self.port_hits,
            "patterns": self.raw_patterns[:5],
        }


async def run(logs: list[CIRunLog]) -> PatternSignal:
    """Analyse last N CI run logs and classify failure patterns."""
    sig = PatternSignal()
    for log in logs:
        blob = log.log_excerpt.lower()
        for pat in _TIMING_PATTERNS:
            if pat.search(blob):
                sig.timing_hits += 1
                sig.raw_patterns.append(f"timing:{pat.pattern[:30]}")
                break
        for pat in _STATE_PATTERNS:
            if pat.search(blob):
                sig.state_hits += 1
                sig.raw_patterns.append(f"state:{pat.pattern[:30]}")
                break
        for pat in _PORT_PATTERNS:
            if pat.search(blob):
                sig.port_hits += 1
                sig.raw_patterns.append(f"port:{pat.pattern[:30]}")
                break
    return sig
