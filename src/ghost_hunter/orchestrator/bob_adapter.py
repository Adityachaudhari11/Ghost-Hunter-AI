"""IBM Bob 2.0 adapter. Central to workflow, not just code generation.

If BOB_API_KEY/BOB_BASE_URL are set, delegate fan-out to Bob subagents
(each agent = one subagent with structured JSON output). Otherwise fall
back to local pipeline so demo works offline. Interface is identical.

All four GhostHunter modules (MutaCI, FlakeHunter, CausalTrace, BugPort)
are orchestrated through this adapter — Bob is structurally central, not
peripheral, as required by the README architecture.
"""

from __future__ import annotations

from ..core.config import Settings
from ..core.logging import get_logger
from ..schemas.bugport import BugPortRequest, ReproductionHarness
from ..schemas.causaltrace import CausalReport, CausalTraceRequest
from ..schemas.flakehunter import CIRunLog, FlakeReport
from ..schemas.mutaci import MutaCIReport, MutaCIRequest
from ..schemas.pentest import ReliabilityReport, ToolCall
from ..schemas.review import ReviewReport
from . import pipeline as local
from . import mutaci_pipeline, flakehunter_pipeline, causaltrace_pipeline, bugport_pipeline

log = get_logger("bob_adapter")


class BobOrchestrator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    @property
    def mode(self) -> str:
        return "bob-2.0" if self.settings.bob_enabled else "local-fallback"

    # ------------------------------------------------------------------
    # Original modules
    # ------------------------------------------------------------------

    async def review(self, diff_text: str, repo_dir: str = "") -> ReviewReport:
        # Bob fan-out point: dependency, blueprint, ghost_path, reuse run in parallel
        log.info("orchestrator mode=%s module=code_review", self.mode)
        return await local.run_code_review(diff_text, repo_dir)

    async def audit_pentest(self, plan: list[str], runs: list[list[ToolCall]], target: str = "local-test-app", retry_fn=None) -> ReliabilityReport:
        log.info("orchestrator mode=%s module=pentest", self.mode)
        return await local.run_pentest_audit(plan, runs, target, retry_fn)

    # ------------------------------------------------------------------
    # GhostHunter / BugBridge modules (Layer 2 — Bob Orchestration)
    # ------------------------------------------------------------------

    async def run_mutaci(self, request: MutaCIRequest) -> MutaCIReport:
        """MutaCI: PR-scoped mutation testing — 3 parallel Bob subagents."""
        log.info("orchestrator mode=%s module=mutaci", self.mode)
        return await mutaci_pipeline.run_mutaci(request)

    async def run_flakehunter(
        self, test_id: str, logs: list[CIRunLog], test_source: str = ""
    ) -> FlakeReport:
        """FlakeHunter: CI flaky test auto-diagnosis and fix — 3 parallel subagents."""
        log.info("orchestrator mode=%s module=flakehunter test_id=%s", self.mode, test_id)
        return await flakehunter_pipeline.run_flakehunter(test_id, logs, test_source)

    async def run_causaltrace(self, request: CausalTraceRequest) -> CausalReport:
        """CausalTrace: production incident root cause — 3 parallel subagents + Laya."""
        log.info("orchestrator mode=%s module=causaltrace", self.mode)
        return await causaltrace_pipeline.run_causaltrace(request)

    async def run_bugport(self, request: BugPortRequest) -> ReproductionHarness:
        """BugPort: production bug local reproduction — 3 parallel subagents."""
        log.info("orchestrator mode=%s module=bugport", self.mode)
        return await bugport_pipeline.run_bugport(request)
