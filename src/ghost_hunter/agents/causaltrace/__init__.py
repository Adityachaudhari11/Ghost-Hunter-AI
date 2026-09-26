"""CausalTrace agents — 3 parallel Bob subagents + causal synthesizer.

Subagent A: TraceAgent  — fetch distributed trace / parse Sentry/Datadog
Subagent B: GitAgent    — git log + PR diffs for affected module
Subagent C: TicketAgent — fetch linked issue / acceptance criteria
Laya Score: rank candidate root causes by likelihood
Synthesizer: compose causal narrative from all three signals
"""

from __future__ import annotations
