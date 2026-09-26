"""Subagent B: GitAgent — run git log on affected module + read PR diffs.

Reads commit history of the affected service directory to find the commit
that introduced the bug.  Works on any local git repo; falls back to demo
data if the repo path is unavailable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ...schemas.causaltrace import GitCommit


def _run_git(args: list[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout
    except Exception:
        return ""


async def run(
    repo_dir: str,
    affected_service: str = "",
    max_commits: int = 10,
) -> list[GitCommit]:
    """Fetch recent commits for the affected service path."""
    if not repo_dir or not Path(repo_dir).is_dir():
        return _demo_commits()
    path_filter = affected_service.replace("-service", "").replace("-", "/") if affected_service else ""
    log_args = [
        "log",
        f"--max-count={max_commits}",
        "--pretty=format:%H|%ae|%s|%ci",
        "--",
        f"*{path_filter}*" if path_filter else ".",
    ]
    raw = _run_git(log_args, repo_dir)
    if not raw.strip():
        return _demo_commits()
    commits: list[GitCommit] = []
    for line in raw.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        sha, author, message, timestamp = parts
        # Get files changed in this commit
        files_raw = _run_git(["diff-tree", "--no-commit-id", "-r", "--name-only", sha.strip()], repo_dir)
        files = [f.strip() for f in files_raw.splitlines() if f.strip()]
        # Get a short diff excerpt
        diff_raw = _run_git(["show", "--stat", "--oneline", sha.strip()], repo_dir)
        commits.append(
            GitCommit(
                sha=sha.strip(),
                author=author.strip(),
                message=message.strip(),
                timestamp=timestamp.strip(),
                files_changed=files[:10],
                diff_excerpt=diff_raw[:500],
            )
        )
    return commits or _demo_commits()


def _demo_commits() -> list[GitCommit]:
    """Pre-recorded demo commits that mirror the README causal story."""
    return [
        GitCommit(
            sha="deadbeef447",
            author="dev@example.com",
            message="simplify checkout: remove null-check on user.paymentMethod",
            timestamp="2025-01-15T14:23:00+00:00",
            pr_number=447,
            files_changed=["src/payment/checkout.py", "src/payment/charge.py"],
            diff_excerpt=(
                "-    if user.paymentMethod is None:\n"
                "-        raise PaymentError('No payment method')\n"
                "+    # removed: guest checkout not in scope per ticket"
            ),
        ),
        GitCommit(
            sha="cafebabe321",
            author="dev2@example.com",
            message="feat: add guest checkout flow",
            timestamp="2025-01-10T09:11:00+00:00",
            pr_number=432,
            files_changed=["src/checkout/guest.py"],
            diff_excerpt="+def guest_checkout(cart): ...",
        ),
    ]
