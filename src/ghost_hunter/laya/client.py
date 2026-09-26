"""Laya AI client — wraps self-hosted ONNX model or heuristic fallback.

Usage:
    from ghost_hunter.laya.client import laya
    result = await laya.choice("What type of failure?", ["async", "state", "ordering", "env"], context)
    score  = await laya.score("Severity of mutant?", context, scale=(1, 10))
    safe   = await laya.noul("Does this patch touch auth paths?", context)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class LayaResult:
    value: Any          # str for Choice, float for Score/Noul
    confidence: float   # 0.0–1.0
    source: str         # "laya-model" | "heuristic"


class _LazyLaya:
    """Thin wrapper.  If `laya` pip package is installed and LAYA_MODEL_PATH
    is set, use the real ONNX model.  Otherwise fall back to deterministic
    heuristics so the demo works completely offline.
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._tried = False

    def _try_load(self) -> bool:
        if self._tried:
            return self._model is not None
        self._tried = True
        try:
            import importlib
            laya_mod = importlib.import_module("laya")
            import os
            path = os.getenv("LAYA_MODEL_PATH", "")
            if path:
                self._model = laya_mod.load(path)
        except Exception:
            self._model = None
        return self._model is not None

    # ------------------------------------------------------------------
    # Three primitives
    # ------------------------------------------------------------------

    async def choice(
        self,
        question: str,
        options: list[str],
        context: str | dict,
        *,
        default: str | None = None,
    ) -> LayaResult:
        """Pick exactly one option from the list."""
        ctx = context if isinstance(context, str) else json.dumps(context)[:2000]
        if self._try_load():
            try:
                answer = self._model.choice(question, options, ctx)
                return LayaResult(value=answer, confidence=0.9, source="laya-model")
            except Exception:
                pass
        # Heuristic fallback
        value = _heuristic_choice(question, options, ctx)
        if value is None:
            value = default or options[0]
        return LayaResult(value=value, confidence=0.6, source="heuristic")

    async def score(
        self,
        question: str,
        context: str | dict,
        *,
        scale: tuple[int, int] = (1, 10),
        default: float = 5.0,
    ) -> LayaResult:
        """Return numeric score on [scale[0], scale[1]]."""
        ctx = context if isinstance(context, str) else json.dumps(context)[:2000]
        if self._try_load():
            try:
                val = float(self._model.score(question, ctx, *scale))
                return LayaResult(value=val, confidence=0.9, source="laya-model")
            except Exception:
                pass
        val = _heuristic_score(question, ctx, scale)
        return LayaResult(value=val, confidence=0.55, source="heuristic")

    async def noul(
        self,
        question: str,
        context: str | dict,
        *,
        threshold: float = 0.5,
    ) -> LayaResult:
        """Calibrated yes/no probability."""
        ctx = context if isinstance(context, str) else json.dumps(context)[:2000]
        if self._try_load():
            try:
                prob = float(self._model.noul(question, ctx))
                return LayaResult(value=prob >= threshold, confidence=prob, source="laya-model")
            except Exception:
                pass
        prob = _heuristic_noul(question, ctx)
        return LayaResult(value=prob >= threshold, confidence=prob, source="heuristic")


# ---------------------------------------------------------------------------
# Heuristic fallbacks (deterministic keyword matching — no LLM, no text gen)
# ---------------------------------------------------------------------------

_FLAKE_KEYWORDS: dict[str, list[str]] = {
    "async_timing":  ["await", "async", "timeout", "settimeout", "sleep", "timing", "ms", "waitfor", "delay"],
    "state_pollution": ["state", "store", "global", "shared", "authstore", "pollution", "before", "after"],
    "port_collision": ["port", "eaddrinuse", "address in use", "bind", "socket"],
    "test_ordering": ["order", "predecessor", "depends on", "ordering", "before", "sequence"],
    "environment": ["env", "environment", "ci", "docker", "path", "variable", "missing"],
}

_SEVERITY_HIGH = ["null", "auth", "security", "payment", "crash", "critical", "oom", "outofmemory"]
_SEVERITY_MED  = ["warning", "error", "fail", "exception", "missing", "invalid"]


def _heuristic_choice(question: str, options: list[str], ctx: str) -> str | None:
    low = (question + " " + ctx).lower()
    # flake root cause routing
    if any(o in _FLAKE_KEYWORDS for o in options):
        best, best_score = options[0], -1
        for opt in options:
            kws = _FLAKE_KEYWORDS.get(opt, [opt])
            s = sum(1 for k in kws if k in low)
            if s > best_score:
                best_score, best = s, opt
        return best
    # generic: pick option whose keyword appears in context
    for opt in options:
        if opt.replace("_", " ").lower() in low or opt.lower() in low:
            return opt
    return None


def _heuristic_score(question: str, ctx: str, scale: tuple[int, int]) -> float:
    low = (question + " " + ctx).lower()
    lo, hi = scale
    mid = (lo + hi) / 2
    boost = sum(2 for w in _SEVERITY_HIGH if w in low)
    boost += sum(1 for w in _SEVERITY_MED if w in low)
    # survived mutant / gap scoring
    if re.search(r"surviv|mutant|gap|behavioral", low):
        raw = min(hi, mid + boost * 0.5)
    else:
        raw = max(lo, mid - 1 + boost * 0.3)
    return round(max(lo, min(hi, raw)), 1)


def _heuristic_noul(question: str, ctx: str) -> float:
    low = (question + " " + ctx).lower()
    security_terms = ["auth", "security", "password", "token", "secret", "permission", "admin", "pii"]
    hits = sum(1 for t in security_terms if t in low)
    if hits >= 3:
        return 0.85
    if hits == 2:
        return 0.7
    if hits == 1:
        return 0.55
    return 0.2


# Singleton — import this everywhere
laya = _LazyLaya()
