"""Safety gate — Laya Noul checks before any PR is auto-opened.

Architecture note (README):
  [LAYER 1 AGAIN: LAYA — Safety gate]
  "Does this patch touch security-sensitive paths?" (Noul)
  "Is the fix semantically consistent with the PR description?" (Noul)
  → PR Opened (only if Laya safety gate passes)

All four modules route their patches through here before opening a PR.
"""

from __future__ import annotations

from dataclasses import dataclass

from .openrewrite import PatchResult
from ..laya.client import laya

_AUTH_PATHS = [
    "auth", "login", "logout", "password", "token", "jwt",
    "session", "permission", "role", "admin", "secret", "key",
    "oauth", "saml", "credential",
]


@dataclass
class SafetyDecision:
    approved: bool
    reason: str
    auth_risk: bool
    confidence_ok: bool


async def evaluate(
    patch: PatchResult,
    pr_description: str = "",
    min_confidence: float = 0.5,
) -> SafetyDecision:
    """Gate the patch.  Returns SafetyDecision(approved=True) only if safe."""
    # Must be compile-safe
    if not patch.compile_safe:
        return SafetyDecision(
            approved=False,
            reason="Patch failed compile safety check — not opening PR",
            auth_risk=False,
            confidence_ok=False,
        )

    # Laya Noul: does patch touch auth/security paths?
    auth_ctx = {
        "patch_description": patch.description,
        "changed_file": patch.file,
        "patch_content": (patch.patched or "")[:500],
    }
    auth_result = await laya.noul(
        "Does this patch modify authentication, authorization, or security-sensitive code paths?",
        auth_ctx,
    )
    if auth_result.value:
        return SafetyDecision(
            approved=False,
            reason=(
                f"Laya safety gate: patch touches security-sensitive paths "
                f"(confidence={auth_result.confidence:.2f}). Manual review required."
            ),
            auth_risk=True,
            confidence_ok=False,
        )

    # Laya Score: confidence in fix correctness
    fix_ctx = {
        "patch_description": patch.description,
        "pr_description": pr_description,
        "method": patch.method,
    }
    score_result = await laya.score(
        "How confident are you that this patch is semantically correct and safe to merge?",
        fix_ctx,
        scale=(1, 10),
    )
    confidence = float(score_result.value) / 10.0
    if confidence < min_confidence:
        return SafetyDecision(
            approved=False,
            reason=f"Laya score {confidence:.2f} below threshold {min_confidence} — needs human review",
            auth_risk=False,
            confidence_ok=False,
        )

    return SafetyDecision(
        approved=True,
        reason=f"Safety gate passed (auth_risk=False, confidence={confidence:.2f})",
        auth_risk=False,
        confidence_ok=True,
    )
