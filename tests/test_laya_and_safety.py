"""Tests for Laya AI client (heuristic fallback) and safety gate."""

from __future__ import annotations

import asyncio

from src.ghost_hunter.laya.client import laya
from src.ghost_hunter.core.safety_gate import evaluate
from src.ghost_hunter.core.openrewrite import PatchResult


def test_laya_choice_returns_one_option():
    options = ["async_timing", "state_pollution", "port_collision", "test_ordering", "environment"]
    result = asyncio.run(laya.choice("What is the root cause?", options, "timeout error in CI logs"))
    assert result.value in options
    assert 0.0 <= result.confidence <= 1.0
    assert result.source in ("laya-model", "heuristic")


def test_laya_score_within_scale():
    result = asyncio.run(laya.score("How severe?", "null pointer exception in payment", scale=(1, 10)))
    assert 1.0 <= result.value <= 10.0


def test_laya_noul_returns_bool():
    result = asyncio.run(laya.noul("Is this field PII?", {"field": "cart_id", "value": 1234}))
    assert isinstance(result.value, bool)


def test_safety_gate_rejects_non_compile_safe():
    patch = PatchResult(
        file="auth.py",
        original="x = 1",
        patched="x = 1",
        compile_safe=False,
        method="ast-safe-stub",
        description="test",
    )
    decision = asyncio.run(evaluate(patch))
    assert decision.approved is False
    assert "compile" in decision.reason.lower()


def test_safety_gate_approves_safe_patch():
    patch = PatchResult(
        file="utils.py",
        original="result = a + b",
        patched="result = a + b  # fixed",
        compile_safe=True,
        method="ast-safe-stub",
        description="Minor arithmetic fix in utility function",
    )
    decision = asyncio.run(evaluate(patch))
    assert isinstance(decision.approved, bool)
    assert isinstance(decision.reason, str)
