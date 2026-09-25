"""Unified diff parsing. No network. Pure stdlib so CLI/API/GHA share it."""

from __future__ import annotations

import re

from ..schemas.review import ChangedFile

_HUNK_FILE = re.compile(r"^\+\+\+\s+b/(.+)$")
_NEW_LINE = re.compile(r"^\+(?!\+\+)(.*)$")

IMPORT_PY = re.compile(r"^\s*(import\s+[\w\.]+|from\s+[\w\.]+\s+import\s+.+)")
IMPORT_JS = re.compile(r"""^\s*(import\s+.*from\s+['"]|require\s*\(\s*['"]|export\s+.*from\s+['"])""")


def parse_diff(diff_text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    new_lineno = 0
    for raw in diff_text.splitlines():
        m = _HUNK_FILE.match(raw)
        if m:
            if current:
                files.append(current)
            current = ChangedFile(path=m.group(1).strip())
            continue
        if raw.startswith("@@"):
            # @@ -a,b +c,d @@ — new file starts at c
            try:
                part = raw.split("+", 1)[1]
                new_lineno = int(part.split(",")[0].split()[0]) - 1
            except (IndexError, ValueError):
                new_lineno = 0
            if current is not None:
                current.hunks.append(raw)
            continue
        if current is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            new_lineno += 1
            current.added_lines.append((new_lineno, raw[1:]))
        elif raw.startswith("-") and not raw.startswith("---"):
            pass
        else:
            new_lineno += 1
    if current:
        files.append(current)
    return files


def extract_new_imports(files: list[ChangedFile]) -> dict[str, list[str]]:
    """file -> raw added import lines (caller resolves package names)."""
    out: dict[str, list[str]] = {}
    for f in files:
        imports = []
        for _, text in f.added_lines:
            if IMPORT_PY.match(text) or IMPORT_JS.match(text):
                imports.append(text.strip())
        if imports:
            out[f.path] = imports
    return out


def resolve_python_package(import_line: str) -> str:
    s = import_line.strip()
    if s.startswith("import "):
        return s.split()[1].split(".")[0].strip()
    if s.startswith("from "):
        return s.split()[1].split(".")[0].strip()
    return ""


def resolve_js_package(import_line: str) -> str:
    m = re.search(r"""['"]([^'"]+)['"]""", import_line)
    if not m:
        return ""
    pkg = m.group(1)
    if pkg.startswith(".") or pkg.startswith("/"):
        return ""  # relative, not external
    # scoped: @org/name -> keep scope/name; bare: first segment
    if pkg.startswith("@"):
        parts = pkg.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else pkg
    return pkg.split("/")[0]
