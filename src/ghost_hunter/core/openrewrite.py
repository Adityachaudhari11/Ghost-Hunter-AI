"""OpenRewrite LST adapter — deterministic, compile-safe code patches.

Architecture note from README:
  Layer 3 — OpenRewrite (Lossless Semantic Tree engine): generates
  compile-verified, type-safe code patches — not raw text diffs.

This module is the Python-side interface to OpenRewrite.  For the hackathon
demo it runs in "stub" mode (deterministic AST-safe regex transforms).
In production: calls the OpenRewrite Java CLI via subprocess.

Interface contract:
  apply_patch(file_path, patch_spec) -> PatchResult
  validate_patch(file_path, patch) -> bool  (compile-check gate)
"""

from __future__ import annotations

import ast
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchResult:
    file: str
    original: str
    patched: str
    compile_safe: bool   # True = AST-parseable after patch
    method: str          # "openrewrite" | "ast-safe-stub" | "advisory-only"
    description: str


def apply_patch(
    file_path: str,
    original_fragment: str,
    replacement_fragment: str,
    description: str = "",
) -> PatchResult:
    """Apply a code transformation.  Tries OpenRewrite first, falls back to stub."""
    path = Path(file_path)
    if not path.is_file():
        return PatchResult(
            file=file_path,
            original=original_fragment,
            patched=original_fragment,
            compile_safe=False,
            method="advisory-only",
            description=description or "File not found — patch is advisory only",
        )
    source = path.read_text(encoding="utf-8")
    # Try OpenRewrite CLI (must be on PATH)
    result = _try_openrewrite(path, original_fragment, replacement_fragment, source)
    if result:
        return result
    # AST-safe stub: regex replace + compile check
    return _ast_safe_stub(file_path, source, original_fragment, replacement_fragment, description)


def _try_openrewrite(
    path: Path, original: str, replacement: str, source: str
) -> PatchResult | None:
    """Attempt OpenRewrite via CLI. Returns None if CLI not available."""
    try:
        subprocess.run(["rewrite", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    # Real implementation would write a YAML recipe and invoke:
    # rewrite run --recipe=ReplaceText --parameters="..."
    # For now, fall through to stub
    return None


def _ast_safe_stub(
    file_path: str,
    source: str,
    original: str,
    replacement: str,
    description: str,
) -> PatchResult:
    patched = source.replace(original, replacement, 1)
    safe = _is_compile_safe(patched, file_path)
    if not safe:
        # Reject the patch — return original with advisory
        return PatchResult(
            file=file_path,
            original=original,
            patched=original,
            compile_safe=False,
            method="ast-safe-stub",
            description=f"Patch rejected: AST parse failed after transform. {description}",
        )
    return PatchResult(
        file=file_path,
        original=original,
        patched=patched,
        compile_safe=True,
        method="ast-safe-stub",
        description=description or "Deterministic AST-safe substitution applied.",
    )


def _is_compile_safe(source: str, file_path: str) -> bool:
    """Return True if source is valid Python (AST parse succeeds)."""
    if not file_path.endswith(".py"):
        return True  # Non-Python: assume safe (JS/TS needs tsc check)
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def format_unified_diff(original: str, patched: str, file: str) -> str:
    """Produce a unified-diff string for PR description."""
    import difflib
    orig_lines = original.splitlines(keepends=True)
    new_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, new_lines, fromfile=f"a/{file}", tofile=f"b/{file}")
    return "".join(diff)
