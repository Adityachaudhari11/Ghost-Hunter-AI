"""Subagent C: TicketAgent — fetch linked issue / acceptance criteria.

Reads the GitHub issue linked to the PR to extract intent and scope.
Falls back to demo data if API is unavailable.
"""

from __future__ import annotations

import httpx

from ...schemas.causaltrace import TicketContext


async def run(
    repo: str = "",
    pr_number: int = 0,
    token: str = "",
    issue_url: str = "",
) -> TicketContext:
    """Fetch ticket/issue context. Returns demo context if API unavailable."""
    if repo and pr_number and token and "REPLACE_ME" not in token:
        ctx = await _fetch_github_issue(repo, pr_number, token)
        if ctx:
            return ctx
    if issue_url:
        return TicketContext(ticket_id=issue_url, title="See linked issue", scope="see ticket")
    return _demo_ticket()


async def _fetch_github_issue(repo: str, pr_number: int, token: str) -> TicketContext | None:
    """Fetch PR body from GitHub; parse acceptance criteria from it."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers={"Authorization": f"Bearer {token}"})
            if r.status_code != 200:
                return None
            data = r.json()
            body = data.get("body") or ""
            return TicketContext(
                ticket_id=f"PR #{pr_number}",
                title=data.get("title", ""),
                description=body[:1000],
                acceptance_criteria=_extract_ac(body),
                scope=_extract_scope(body),
            )
    except Exception:
        return None


def _extract_ac(body: str) -> str:
    import re
    m = re.search(r"(?:acceptance criteria|## checklist)([\s\S]{0,600})", body, re.I)
    return m.group(1).strip() if m else ""


def _extract_scope(body: str) -> str:
    import re
    m = re.search(r"(?:scope|applies to|for)([:.\s]+[^\n]{0,120})", body, re.I)
    return m.group(1).strip() if m else "not specified"


def _demo_ticket() -> TicketContext:
    return TicketContext(
        ticket_id="TICKET-891",
        title="Simplify logged-in checkout flow",
        description="Remove unnecessary null checks for logged-in users to reduce code complexity.",
        acceptance_criteria="- Checkout succeeds for all logged-in users\n- No regression on existing tests",
        scope="logged-in users only — guest checkout not in scope",
    )
