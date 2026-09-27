"""Scanner 2 — Semantic Grep / Blueprint Asserter.

Gatekeeper that checks new code against the team's high-level
architecture rules (the "blueprint"). Default rule pack catches the
classic AI-slop violations:

- RAW_SQL ......... raw SQL string in execute/query/raw() instead of the
                    designated ORM wrapper (e.g. ``db.query(...)``)
- CUSTOM_TIME ..... hand-rolled timestamp formatting via strftime/format
                    instead of the internal ``format_timestamp`` helper
- DIRECT_ENV ...... direct ``os.environ`` / ``process.env`` access outside
                    a config module instead of the central config
- PRINT_LOG ....... ``print()`` / ``console.log`` in shipped code instead
                    of the structured logger
- RAW_HTTP ........ direct ``fetch(`` / ``axios.`` instead of the internal
                    API client wrapper

Custom rules: pass ``--blueprint rules.json`` — a JSON list of
``{id, title, pattern, severity, message, fix, extensions}`` which is
*added* to the defaults (a custom rule with the same id overrides it).
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RULES = [
    {
        "id": "RAW_SQL",
        "title": "Raw SQL instead of ORM wrapper",
        "pattern": r"(?i)\b(execute|executemany|query|raw)\s*\(\s*[fFrRbBuU]?['\"`][^'\"`]*\b(SELECT|INSERT|UPDATE|DELETE)\b",
        "extensions": [".py", ".ts", ".js"],
        "severity": 8,
        "message": "Raw SQL string — use the designated ORM wrapper (db.query / repository layer).",
        "fix": "Move the query into the repository/ORM layer with parameterised bindings.",
    },
    {
        "id": "CUSTOM_TIME",
        "title": "Reinvented timestamp formatter",
        "pattern": r"strftime\s*\(|\btoISOString\s*\(\s*\)\s*\.\s*(slice|split|replace)\b|getMonth\(\)\s*/",
        "extensions": [".py", ".ts", ".js"],
        "severity": 6,
        "message": "Hand-rolled timestamp formatting — use the internal format_timestamp helper.",
        "fix": "Replace with format_timestamp(dt) from utils/time so output stays consistent.",
    },
    {
        "id": "DIRECT_ENV",
        "title": "Direct env access outside config",
        "pattern": r"os\.environ\s*\[|process\.env\.[A-Z_]+",
        "extensions": [".py", ".ts", ".js"],
        "severity": 5,
        "message": "Direct environment access — route through the central config module.",
        "fix": "Read this key once in config.py/.ts and import it from there.",
    },
    {
        "id": "PRINT_LOG",
        "title": "print/console.log in shipped code",
        "pattern": r"(?<![\w.])print\s*\(|console\.(log|debug|info)\s*\(",
        "extensions": [".py", ".ts", ".js"],
        "severity": 4,
        "message": "Unstructured print/console logging — use the structured logger.",
        "fix": "Replace with logger.info(...) so logs stay searchable.",
    },
    {
        "id": "RAW_HTTP",
        "title": "Raw HTTP instead of API client",
        "pattern": r"(?<![\w.])fetch\s*\(|axios\.(get|post|put|delete)\s*\(",
        "extensions": [".ts", ".js"],
        "severity": 6,
        "message": "Raw HTTP call — use the internal API client wrapper (retries/auth/headers).",
        "fix": "Call apiClient.get/post/... instead of fetch/axios directly.",
    },
]

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}


@dataclass
class Rule:
    id: str
    title: str
    pattern: str
    severity: int
    message: str
    fix: str
    extensions: list = field(default_factory=list)
    rx: re.Pattern = field(init=False, repr=False)

    def __post_init__(self):
        self.rx = re.compile(self.pattern)


def load_rules(custom_path: str = "") -> list[Rule]:
    merged: dict[str, dict] = {r["id"]: dict(r) for r in DEFAULT_RULES}
    if custom_path:
        try:
            extra = json.loads(Path(custom_path).read_text(encoding="utf-8"))
            for r in extra if isinstance(extra, list) else extra.get("rules", []):
                merged[r["id"]] = r
        except Exception as e:
            print(f"[Blueprint] Could not load custom rules ({e}) — using defaults.")
    return [Rule(**r) for r in merged.values()]


def _is_config_module(path: Path) -> bool:
    return path.stem.lower() in {"config", "settings", "env"} or "config" in path.parts


def scan_blueprint(target: str, custom_rules: str = "") -> list[dict]:
    """Grep target files for blueprint violations. Returns finding dicts."""
    root = Path(target).resolve()
    rules = load_rules(custom_rules)
    findings: list[dict] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for rule in rules:
                if rule.extensions and p.suffix.lower() not in rule.extensions:
                    continue
                if rule.id == "DIRECT_ENV" and _is_config_module(p):
                    continue  # env access IS the config module's job
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", "//")):
                        continue
                    if rule.rx.search(line):
                        findings.append({
                            "id": f"BLUE-{len(findings) + 1:02d}",
                            "scanner": "blueprint",
                            "rule": rule.id,
                            "severity": rule.severity,
                            "file": str(p), "line": i,
                            "message": f"\U0001f7e0 [{rule.id}] {rule.title}: {rule.message}",
                            "code": stripped[:160],
                            "fix": rule.fix,
                        })
    return findings
