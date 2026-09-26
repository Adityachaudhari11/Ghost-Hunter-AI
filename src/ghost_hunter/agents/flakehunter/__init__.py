"""FlakeHunter agents — 3 parallel Bob subagents + fix generator.

Subagent A: PatternAgent   — analyse CI logs for failure timing/patterns
Subagent B: CodeAgent      — read test file for async/state issues
Subagent C: OrderingAgent  — correlate which predecessor test causes failure
Laya Choice: classify root cause
Fix generator: deterministic fix per root cause class
"""

from __future__ import annotations
