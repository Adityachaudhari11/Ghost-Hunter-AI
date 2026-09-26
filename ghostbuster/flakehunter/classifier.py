"""
FlakeHunter — CI Failure Pattern Classifier.

Takes a CI test failure log and uses Laya AI to classify the root cause,
then returns a structured diagnosis with a targeted fix template.

Root cause categories (from academic literature + industry patterns):
  async       — timing assumptions, hardcoded sleeps, unresolved promises
  state       — shared mutable state, missing teardown, test ordering dependency
  ordering    — test depends on another test running first
  environment — port conflicts, missing env vars, network calls, filesystem
  resource    — OOM, CPU throttling, disk limits
"""

from dataclasses import dataclass
from typing import Optional

# Root cause → fix template
FIX_TEMPLATES: dict[str, str] = {
    "async": (
        "Replace hardcoded `setTimeout`/`sleep` with `waitFor`/`vi.waitFor`/polling until condition is met. "
        "Ensure all async operations are properly awaited and Promises resolved before assertions."
    ),
    "state": (
        "Isolate shared state: move setup into `beforeEach` (not `beforeAll`), "
        "reset mocks with `jest.clearAllMocks()` in `afterEach`, "
        "and ensure each test creates its own independent fixtures."
    ),
    "ordering": (
        "Make this test self-contained: eliminate the dependency on another test's side effects. "
        "Add the required precondition as explicit setup in `beforeEach` for this describe block."
    ),
    "environment": (
        "Mock external dependencies (network calls, ports, env vars) with `jest.mock` or `nock`. "
        "Use `process.env.TEST_PORT || randomPort()` to avoid port conflicts in parallel runs."
    ),
    "resource": (
        "Increase Jest memory with `--max-old-space-size=4096` or reduce `--maxWorkers`. "
        "Profile with `--detectOpenHandles` to find unclosed connections."
    ),
}

# Keywords by category for demo context scoring
CATEGORY_SIGNALS: dict[str, list[str]] = {
    "async": ["timeout", "async", "await", "promise", "settimeout", "delay", "timer", "race condition", "timed out"],
    "state": ["global", "shared", "beforeall", "afterall", "reset", "mutation", "pollut", "contaminate", "stale"],
    "ordering": ["order", "sequence", "depend", "before", "after", "require", "predecessor"],
    "environment": ["port", "network", "http", "env", "external", "api", "econnrefused", "eaddrinuse", "socket"],
    "resource": ["memory", "cpu", "disk", "oom", "limit", "killed", "heap", "out of memory"],
}


@dataclass
class FlakeClassification:
    category: str           # one of the 5 categories
    confidence: float       # 0.0 – 1.0
    reasoning: str          # plain-English explanation
    fix_template: str       # actionable fix for this category
    affected_line: Optional[str] = None  # suspicious line from the log


def classify_flake(log: str, laya_client) -> FlakeClassification:
    """
    Use Laya AI to classify the flake root cause from a CI failure log.
    Returns a structured diagnosis with fix template.
    """
    categories = list(FIX_TEMPLATES.keys())

    # Laya choice: which category?
    category = laya_client.choice(
        context=f"CI test failure log:\n{log[:1200]}",
        options=categories,
    )

    # Laya score: how confident?
    confidence_raw = laya_client.score(
        context=f"Category '{category}' was chosen for this CI log:\n{log[:800]}",
        scale=(1, 10),
    )
    confidence = round(confidence_raw / 10.0, 2)

    # Find the most suspicious line
    affected_line = _find_suspicious_line(log, category)

    reasoning = _build_reasoning(log, category, affected_line)

    return FlakeClassification(
        category=category,
        confidence=confidence,
        reasoning=reasoning,
        fix_template=FIX_TEMPLATES[category],
        affected_line=affected_line,
    )


def _find_suspicious_line(log: str, category: str) -> Optional[str]:
    """Find the most likely culprit line in the log for the given category."""
    signals = CATEGORY_SIGNALS.get(category, [])
    for line in log.splitlines():
        line_lower = line.lower()
        if any(sig in line_lower for sig in signals):
            return line.strip()
    # Fallback: return the line with "Error" or the first non-empty line
    for line in log.splitlines():
        if "error" in line.lower() or "fail" in line.lower():
            return line.strip()
    return None


def _build_reasoning(log: str, category: str, suspicious_line: Optional[str]) -> str:
    templates = {
        "async": "Log shows timing-related failure — likely a race condition or hardcoded delay.",
        "state": "Log shows state contamination — a previous test left side effects that broke this one.",
        "ordering": "Log shows test ordering dependency — this test requires another test to run first.",
        "environment": "Log shows environment-specific failure — port conflict, missing env var, or network dependency.",
        "resource": "Log shows resource exhaustion — memory, CPU, or file descriptor limit reached.",
    }
    base = templates.get(category, f"Classified as {category}.")
    if suspicious_line:
        base += f"\n  Suspicious line: `{suspicious_line[:120]}`"
    return base
