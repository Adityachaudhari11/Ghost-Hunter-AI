"""
Laya AI client — System 1 decision model.
Self-hosted, Apache 2.0, ~33ms latency, cannot hallucinate.
Docs: https://huggingface.co/convaiinnovations/laya

Uses the real RLAgent from laya_model/ (ModernBERT-large backbone).
Falls back to heuristics if model weights are missing or torch is not available.
"""

import os
import sys
from pathlib import Path
from typing import Any

_LAYA_MODEL_DIR = str(Path(__file__).parent.parent.parent / "laya_model")


def _try_load_agent():
    """Load the real RLAgent from laya_model/. Returns agent or None."""
    model_dir = _LAYA_MODEL_DIR
    weights_path = os.path.join(model_dir, "model.safetensors")
    if not os.path.exists(weights_path):
        return None
    try:
        # RLAgent imports from rl_common which must be on path
        if model_dir not in sys.path:
            sys.path.insert(0, model_dir)
        from rl_agent_api import RLAgent
        agent = RLAgent(model_dir)
        return agent
    except Exception as e:
        print(f"[LayaClient] Could not load real model: {e}. Using heuristics.")
        return None


class LayaClient:
    """
    Wrapper for Laya AI decision model (System 1).
    Uses real RLAgent when model.safetensors is present; heuristics otherwise.
    """

    def __init__(self):
        self._agent = _try_load_agent()
        if self._agent is not None:
            print("[LayaClient] Real Laya model loaded (ModernBERT-large)")
        else:
            print("[LayaClient] Heuristic mode (model weights not loaded)")

    def choice(self, context: str, options: list[str]) -> str:
        """Pick one option from the list given the context."""
        if self._agent is not None:
            try:
                result = self._agent.system_one(
                    state=context,
                    questions={
                        "q": {
                            "type": "choice",
                            "instructions": f"Given the context, which option best applies?\nContext: {context}",
                            "criteria": {opt: None for opt in options},
                        }
                    },
                )
                return result["answers"]["q"]["choice"]
            except Exception as e:
                print(f"[LayaClient] Real inference failed: {e}. Falling back.")
        return self._heuristic_choice(context, options)

    def score(self, context: str, scale: tuple[int, int] = (1, 10)) -> float:
        """Return a numeric score in the given range."""
        if self._agent is not None:
            try:
                n_levels = scale[1] - scale[0] + 1
                # Build score criteria as ordered list of level descriptions
                criteria = [
                    f"level {i}: severity {scale[0] + i}" for i in range(n_levels)
                ]
                result = self._agent.system_one(
                    state=context,
                    questions={
                        "q": {
                            "type": "score",
                            "instructions": (
                                "Rate how severe this behavioral gap is for production correctness. "
                                f"Scale: {scale[0]}=trivial whitespace/log change, "
                                f"{(scale[0]+scale[1])//2}=boundary condition or edge case, "
                                f"{scale[1]}=security/payment/data-loss bug. "
                                f"Context: {context}"
                            ),
                            "criteria": criteria,
                        }
                    },
                )
                # raw_score is a float 0..(n_levels-1), map to scale
                raw = result["answers"]["q"]["score"]
                mapped = scale[0] + raw * (scale[1] - scale[0]) / max(n_levels - 1, 1)
                return round(mapped, 1)
            except Exception as e:
                print(f"[LayaClient] Real inference failed: {e}. Falling back.")
        return self._heuristic_score(context, scale)

    def noul(self, statement: str) -> float:
        """Return calibrated probability (0.0–1.0) that statement is true."""
        if self._agent is not None:
            try:
                result = self._agent.system_one(
                    state=statement,
                    questions={
                        "q": {
                            "type": "noul",
                            "instructions": statement,
                            "criteria": None,
                        }
                    },
                )
                return float(result["answers"]["q"]["noul"])
            except Exception as e:
                print(f"[LayaClient] Real inference failed: {e}. Falling back.")
        return self._heuristic_noul(statement)

    # ── Heuristic fallbacks (used when model is not available) ─────────────

    def _heuristic_choice(self, context: str, options: list[str]) -> str:
        ctx = context.lower()
        flake_keywords = {
            "async": ["async", "await", "promise", "timeout", "settimeout", "delay"],
            "state": ["global", "shared", "beforeall", "afterall", "reset", "mutation"],
            "ordering": ["order", "sequence", "predecessor", "before", "after", "depends"],
            "environment": ["env", "port", "network", "http", "api", "external"],
            "resource": ["memory", "cpu", "disk", "oom", "limit", "resource"],
        }
        for opt in options:
            key = opt.lower().replace("_", "")
            for category, keywords in flake_keywords.items():
                if category in key and any(kw in ctx for kw in keywords):
                    return opt
        return options[0]

    def _heuristic_score(self, context: str, scale: tuple[int, int]) -> float:
        ctx = context.lower()
        high_signal = ["boundary", "null", "security", "auth", "payment", "negative", "zero", "overflow"]
        low_signal = ["whitespace", "comment", "log", "debug", "print"]
        base = (scale[0] + scale[1]) / 2
        if any(kw in ctx for kw in high_signal):
            return min(scale[1], base + 2.5)
        if any(kw in ctx for kw in low_signal):
            return max(scale[0], base - 2.0)
        return round(base + 0.3, 1)

    def _heuristic_noul(self, statement: str) -> float:
        s = statement.lower()
        negative_signals = ["pii", "personal", "security", "auth", "password", "token", "secret"]
        if any(kw in s for kw in negative_signals):
            return 0.82
        return 0.15
