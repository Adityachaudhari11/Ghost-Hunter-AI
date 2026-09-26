"""Subagent C: OrderingAgent — correlate predecessor tests that cause failures."""

from __future__ import annotations

from collections import Counter

from ...schemas.flakehunter import CIRunLog


class OrderingSignal:
    def __init__(self) -> None:
        self.suspects: list[tuple[str, int]] = []  # (predecessor_test, failure_count)

    def to_dict(self) -> dict:
        return {"suspects": self.suspects[:3]}


async def run(logs: list[CIRunLog]) -> OrderingSignal:
    """Find which predecessor tests correlate with failures."""
    sig = OrderingSignal()
    fail_predecessors: list[str] = []
    for log in logs:
        if log.status == "fail" and log.predecessor_test:
            fail_predecessors.append(log.predecessor_test)
    counts = Counter(fail_predecessors)
    sig.suspects = counts.most_common(3)
    return sig
