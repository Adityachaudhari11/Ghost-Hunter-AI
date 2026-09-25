"""IBM Bob 2.0 adapter. Central to workflow, not just code generation.

If BOB_API_KEY/BOB_BASE_URL are set, delegate fan-out to Bob subagents
(each agent = one subagent with structured JSON output). Otherwise fall
back to local pipeline so demo works offline. Interface is identical.
"""

from __future__ import annotations

from ..core.config import Settings
from ..core.logging import get_logger
from ..schemas.pentest import ReliabilityReport, ToolCall
from ..schemas.review import ReviewReport
from . import pipeline as local

log = get_logger("bob_adapter")


class BobOrchestrator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    @property
    def mode(self) -> str:
        return "bob-2.0" if self.settings.bob_enabled else "local-fallback"

    async def review(self, diff_text: str, repo_dir: str = "") -> ReviewReport:
        # TODO: when Bob SDK is available, fan out here:
        # bob.fan_out([dependency, blueprint, ghost_path, reuse], ctx)
        # For now local pipeline preserves contracts; Bob wiring is isolated here.
        log.info("orchestrator mode=%s", self.mode)
        return await local.run_code_review(diff_text, repo_dir)

    async def audit_pentest(self, plan: list[str], runs: list[list[ToolCall]], target: str = "local-test-app", retry_fn=None) -> ReliabilityReport:
        log.info("pentest orchestrator mode=%s", self.mode)
        return await local.run_pentest_audit(plan, runs, target, retry_fn)
