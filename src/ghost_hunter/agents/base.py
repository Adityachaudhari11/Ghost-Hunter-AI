"""Agent protocol: every agent is importable by CLI, API, GHA, or Bob adapter."""

from __future__ import annotations

from typing import Any, Protocol

from ..schemas.common import Finding


class CodeReviewAgent(Protocol):
    name: str

    async def run(self, *args: Any, **kwargs: Any) -> list[Finding]:
        ...
