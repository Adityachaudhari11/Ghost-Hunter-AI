"""
Stryker runner for MutaCI.
Runs Stryker on specific files and parses the JSON mutation report.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread
from typing import Callable


@dataclass
class Mutant:
    id: str
    mutator_name: str
    replacement: str
    file_path: str
    line: int
    col_start: int
    col_end: int
    original_code: str
    mutated_code: str
    status: str  # "Killed" | "Survived" | "NoCoverage" | "Timeout"
    description: str = ""


@dataclass
class MutationReport:
    total: int = 0
    killed: int = 0
    survived: int = 0
    no_coverage: int = 0
    timeout: int = 0
    score: float = 0.0
    surviving_mutants: list[Mutant] = field(default_factory=list)
    duration_seconds: float = 0.0


def parse_stryker_json(report_path: str) -> MutationReport:
    """Parse Stryker's JSON report into a MutationReport."""
    with open(report_path) as f:
        data = json.load(f)

    report = MutationReport()
    surviving = []

    for file_path, file_data in data.get("files", {}).items():
        for m in file_data.get("mutants", []):
            report.total += 1
            status = m.get("status", "")
            if status == "Killed":
                report.killed += 1
            elif status == "Survived":
                report.survived += 1
                surviving.append(Mutant(
                    id=str(m.get("id", "")),
                    mutator_name=m.get("mutatorName", ""),
                    replacement=m.get("replacement", ""),
                    file_path=file_path,
                    line=m.get("location", {}).get("start", {}).get("line", 0),
                    col_start=m.get("location", {}).get("start", {}).get("column", 0),
                    col_end=m.get("location", {}).get("end", {}).get("column", 0),
                    original_code=m.get("original", ""),
                    mutated_code=m.get("replacement", ""),
                    status=status,
                ))
            elif status == "NoCoverage":
                report.no_coverage += 1
            elif status == "Timeout":
                report.timeout += 1

    denominator = report.total - report.no_coverage
    report.score = (report.killed / denominator * 100) if denominator > 0 else 0.0
    report.surviving_mutants = surviving
    return report


def run_stryker(
    project_path: str,
    target_files: list[str] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> MutationReport:
    """
    Run Stryker mutation testing on the project.
    target_files: limit mutations to these file globs.
    on_progress: callback(killed, total) for live progress display.
    """
    cmd = ["npx", "stryker", "run"]
    if target_files:
        mutate_pattern = ",".join(target_files)
        cmd += ["--mutate", mutate_pattern]

    report_path = os.path.join(project_path, "reports", "mutation", "mutation.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    start = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    killed = 0
    total_seen = 0

    for line in proc.stdout:
        line = line.strip()
        # Parse Stryker's progress output
        if "Killed" in line or "Survived" in line:
            total_seen += 1
            if "Killed" in line:
                killed += 1
            if on_progress:
                on_progress(killed, total_seen)

    proc.wait()
    duration = time.time() - start

    if not os.path.exists(report_path):
        # Return empty report if Stryker failed
        return MutationReport()

    report = parse_stryker_json(report_path)
    report.duration_seconds = duration
    return report


def make_demo_report() -> MutationReport:
    """
    Return a hardcoded demo report for when Stryker is not installed.
    Represents the pricing.ts module with intentionally thin tests.
    """
    surviving = [
        Mutant(
            id="1", mutator_name="ConditionalExpression",
            replacement="true",
            file_path="src/pricing.ts", line=47, col_start=6, col_end=30,
            original_code="discount.value < 0 || discount.value > 100",
            mutated_code="true",
            status="Survived",
            description="No test verifies that 0% discount returns the original price unchanged",
        ),
        Mutant(
            id="2", mutator_name="BooleanLiteral",
            replacement="discount.value <= 0",
            file_path="src/pricing.ts", line=47, col_start=6, col_end=22,
            original_code="discount.value < 0",
            mutated_code="discount.value <= 0",
            status="Survived",
            description="No test verifies that negative percentage discount raises an error",
        ),
        Mutant(
            id="3", mutator_name="ArithmeticOperator",
            replacement="basePrice * (1 + discount.value / 100)",
            file_path="src/pricing.ts", line=52, col_start=12, col_end=45,
            original_code="basePrice * (1 - discount.value / 100)",
            mutated_code="basePrice * (1 + discount.value / 100)",
            status="Survived",
            description="No test verifies that a 100% discount results in $0, not a negative price",
        ),
        Mutant(
            id="4", mutator_name="ConditionalExpression",
            replacement="0",
            file_path="src/pricing.ts", line=61, col_start=12, col_end=35,
            original_code="Math.max(0, basePrice - discount.value)",
            mutated_code="0",
            status="Survived",
            description="No test verifies discount stacking order — applying fixed then % gives different result than % then fixed",
        ),
    ]

    return MutationReport(
        total=48,
        killed=44,
        survived=4,
        no_coverage=0,
        timeout=0,
        score=91.7,
        surviving_mutants=surviving,
        duration_seconds=42.3,
    )
