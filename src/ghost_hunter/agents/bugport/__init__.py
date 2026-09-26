"""BugPort agents — 3 parallel Bob subagents for local reproduction.

Subagent A: EnvironmentAgent — checkout git SHA, generate .env.bugport
Subagent B: DataAgent        — generate SQL fixture from DB query results
Subagent C: StateAgent       — initialize in-memory objects to production state
"""

from __future__ import annotations
