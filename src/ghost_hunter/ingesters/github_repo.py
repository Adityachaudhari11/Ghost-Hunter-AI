"""Materialize a GitHub repo link to a local directory for gray-box review.

Public repos need no token. A token (env GITHUB_TOKEN) is only used for
private repos / rate limits, passed via git http.extraHeader so it never
appears in URLs, logs, or reports.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

_GH_RE = re.compile(
    r"^https://github\.com/(?P<org>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?"
    r"(?:/(?:tree|blob)/(?P<branch>[^/\s]+))?/?$"
)


def parse_github_url(url: str) -> dict[str, str | None]:
    url = (url or "").strip()
    if "/pull/" in url or "/compare/" in url:
        raise ValueError("PR/compare link: use the `review-pr` flow with the PR diff, not prove-repo.")
    m = _GH_RE.match(url)
    if not m:
        raise ValueError("Only https://github.com/<org>/<repo>[/tree/<branch>] links are supported.")
    return {"org": m.group("org"), "repo": m.group("repo"), "branch": m.group("branch")}


def materialize(
    repo_url: str,
    branch: str | None = None,
    dest: str | Path | None = None,
    token: str | None = None,
    timeout: int = 180,
) -> tuple[Path, Callable[[], None]]:
    """Shallow-clone a repo. Returns (path, cleanup). cleanup is a no-op for dest."""
    info = parse_github_url(repo_url)
    br = branch or info["branch"]
    clone_url = f"https://github.com/{info['org']}/{info['repo']}.git"
    target = Path(dest) if dest else Path(tempfile.mkdtemp(prefix="ghost-repo-"))
    base = ["git"]
    if token:
        base += ["-c", "http.extraHeader=Authorization: Bearer REDACTED".replace("REDACTED", token)]
    cmd = base + ["clone", "--depth", "1"]
    if br:
        cmd += ["--branch", br]
    cmd += [clone_url, str(target)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # Never include argv (may hold the token) in the error.
        raise RuntimeError(f"git clone failed for {info['org']}/{info['repo']}: {type(e).__name__}") from None
    if dest:
        return target, lambda: None

    def _cleanup() -> None:
        shutil.rmtree(target, ignore_errors=True)

    return target, _cleanup
