"""GitHub target support — shallow-clone a repo URL for live evaluation.

Keeps SlopWatch usable from Bob IDE / CI where the input is a repo URL,
not a local checkout: ``--target https://github.com/owner/repo``.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

_GITHUB_RE = re.compile(
    r"^(https?://github\.com/[^/\s]+/[^/\s]+?(\.git)?/?"
    r"|git@github\.com:[^/\s]+/[^/\s]+?(\.git)?)$"
)


def is_github_url(target: str) -> bool:
    return bool(_GITHUB_RE.match((target or "").strip()))


def clone_repo(url: str, branch: str = "") -> str:
    """Shallow-clone url into a temp dir. Returns the dir path.

    Raises RuntimeError with a human-readable message on failure.
    Caller owns cleanup (shutil.rmtree) unless --keep-clone is used.
    """
    if not shutil.which("git"):
        raise RuntimeError("`git` binary not found — install git to scan GitHub URLs.")
    tmp = tempfile.mkdtemp(prefix="slopwatch-")
    cmd = ["git", "clone", "--depth", "1", "--no-tags"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [url.rstrip("/"), tmp + "/repo"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        err = (e.stderr or e.stdout or "unknown git error").strip().splitlines()
        raise RuntimeError(f"Clone failed: {err[-1] if err else 'git error'}")
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("Clone timed out after 180s.")
    dest = str(Path(tmp) / "repo")
    print(f"[SlopWatch] Cloned {url} → {dest} (shallow, depth 1)")
    return dest
