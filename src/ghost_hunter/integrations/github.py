"""GitHub integration: PR fetch, comment format, webhook verify. Least privilege."""

from __future__ import annotations

import hashlib
import hmac

import httpx

from ..schemas.review import ReviewReport


async def fetch_pr_diff(repo: str, pr_number: int, token: str) -> str:
    """repo like 'org/name'. Uses PAT from env, never logged."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers={"Accept": "application/vnd.github.diff", "Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.text


def verify_webhook(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature)


def format_comment(report: ReviewReport) -> str:
    lines = [f"## Ghost-Hunter review `{report.review_id}`", f"Found {len(report.findings)} issue(s) requiring review.", ""]
    for f in report.findings:
        lines.append(f"- **[{f.severity.value.upper()}]** `{f.file}:{f.line}` {f.observed} (conf {f.confidence:.2f})")
    lines += ["", "<details><summary>Evidence</summary>", ""]
    for f in report.findings:
        lines.append(f"- {f.finding_id} [{f.source}] rule `{f.rule}` — " + "; ".join(e.ref for e in f.evidence[:3]))
    lines.append("</details>")
    return "\n".join(lines)
