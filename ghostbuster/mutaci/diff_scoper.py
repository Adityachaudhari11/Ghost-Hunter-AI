"""
Parse a git diff and extract per-file changed line ranges.
Used by MutaCI to scope mutation testing to only the PR's changed lines.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileChange:
    path: str
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)

    @property
    def changed_line_ranges(self) -> list[tuple[int, int]]:
        """Return (start, end) ranges of added lines for mutation scoping."""
        if not self.added_lines:
            return []
        ranges = []
        start = self.added_lines[0]
        end = self.added_lines[0]
        for line in self.added_lines[1:]:
            if line == end + 1:
                end = line
            else:
                ranges.append((start, end))
                start = end = line
        ranges.append((start, end))
        return ranges


def parse_diff(diff_text: str) -> list[FileChange]:
    """Parse unified diff text into FileChange objects."""
    changes: list[FileChange] = []
    current_file: FileChange | None = None
    new_line_num = 0

    for line in diff_text.splitlines():
        # New file header
        if line.startswith("+++ b/"):
            path = line[6:]
            current_file = FileChange(path=path)
            changes.append(current_file)

        # Hunk header: @@ -old_start,old_count +new_start,new_count @@
        elif line.startswith("@@") and current_file:
            match = re.search(r"\+(\d+)(?:,\d+)?", line)
            if match:
                new_line_num = int(match.group(1))

        elif current_file:
            if line.startswith("+") and not line.startswith("+++"):
                current_file.added_lines.append(new_line_num)
                new_line_num += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_file.removed_lines.append(new_line_num)
            else:
                new_line_num += 1

    return changes


def get_staged_diff(repo_path: str = ".") -> str:
    """Get the staged diff (what's about to be committed)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0"],
        capture_output=True, text=True, cwd=repo_path
    )
    return result.stdout


def get_pr_diff(base_branch: str = "main", repo_path: str = ".") -> str:
    """Get the diff of the current branch vs base branch."""
    result = subprocess.run(
        ["git", "diff", f"{base_branch}...HEAD", "--unified=0"],
        capture_output=True, text=True, cwd=repo_path
    )
    return result.stdout


def get_changed_ts_files(diff_text: str) -> list[FileChange]:
    """Filter diff to only TypeScript source files (not tests)."""
    changes = parse_diff(diff_text)
    return [c for c in changes if c.path.endswith(".ts") and "/tests/" not in c.path]


def simulate_pr_diff(changed_file: str, start_line: int, end_line: int) -> str:
    """
    Generate a simulated diff for demo purposes.
    In production this comes from git diff or GitHub PR API.
    """
    hunk_size = end_line - start_line + 1
    lines = [
        f"diff --git a/{changed_file} b/{changed_file}",
        f"--- a/{changed_file}",
        f"+++ b/{changed_file}",
        f"@@ -1,3 +{start_line},{hunk_size} @@",
    ]
    for i in range(start_line, end_line + 1):
        lines.append(f"+  // changed line {i}")
    return "\n".join(lines)
