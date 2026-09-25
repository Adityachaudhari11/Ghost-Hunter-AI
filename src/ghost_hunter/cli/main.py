"""CLI: same pipeline as API/GHA. `python -m ghost_hunter.cli.main ...`."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from ..core.config import Settings
from ..core.logging import get_logger, log_safe
from ..orchestrator.bob_adapter import BobOrchestrator
from ..schemas.pentest import ToolCall

log = get_logger("cli")


def _write(report_dir: str, name: str, data: dict) -> str:
    p = Path(report_dir)
    p.mkdir(parents=True, exist_ok=True)
    out = p / name
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(out)


async def _review(args: argparse.Namespace) -> int:
    diff = Path(args.diff).read_text(encoding="utf-8") if args.diff else args.diff_text
    orch = BobOrchestrator(Settings())
    report = await orch.review(diff, args.repo_dir)
    path = _write(Settings().report_dir, f"{report.review_id}.json", report.model_dump())
    log_safe(log, "review complete", {"review_id": report.review_id, "findings": len(report.findings), "report": path})
    print(json.dumps(report.model_dump(), indent=2))
    return 0


async def _pentest(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    runs_raw = json.loads(Path(args.runs).read_text(encoding="utf-8"))
    names = plan if isinstance(plan, list) else plan.get("test_plan", plan.get("checks", []))
    if names and isinstance(names[0], dict):
        names = [n.get("id", n.get("name")) for n in names]
    runs = [[ToolCall(**c) for c in run] for run in runs_raw]
    orch = BobOrchestrator(Settings())
    report = await orch.audit_pentest(names, runs, getattr(args, "target", "local-test-app"))
    path = _write(Settings().report_dir, f"{report.report_id}.json", report.model_dump())
    log_safe(log, "audit complete", {"report_id": report.report_id, "path": path})
    print(json.dumps(report.model_dump(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ghost-hunter", description="Evidence-based verification layer")
    sub = p.add_subparsers(required=True)
    r = sub.add_parser("review-pr", help="Review a unified diff")
    r.add_argument("--diff", default="", help="Path to unified diff file")
    r.add_argument("--diff-text", default="", help="Raw diff text (alternative)")
    r.add_argument("--repo-dir", default="", help="Local repo checkout for context/AST")
    r.set_defaults(fn=_review)
    a = sub.add_parser("audit-pentest", help="Audit pentest runs")
    a.add_argument("--plan", required=True, help="JSON file: list or {test_plan:[...]}")
    a.add_argument("--runs", required=True, help="JSON file: list of runs (each a list of ToolCall dicts)")
    a.add_argument("--target", default="local-test-app")
    a.set_defaults(fn=_pentest)
    return p


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(args.fn(args)))


if __name__ == "__main__":
    main()
