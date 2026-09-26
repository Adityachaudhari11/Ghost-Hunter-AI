"""MutaCI agents (3 parallel Bob subagents).

Subagent A: MutationRunner    — executes/generates mutants scoped to diff
Subagent B: GapClassifier     — uses Laya Score to rank surviving mutants
Subagent C: TestSynthesizer   — generates plain-English test descriptions for real gaps
"""

from __future__ import annotations
