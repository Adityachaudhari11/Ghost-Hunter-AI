"""Risk Correlator: boost priority when signals coincide on same file/lines.

Example: unverified dependency + its usage + missing error handling
=> higher review priority. Severity and confidence stay separate.
"""

from __future__ import annotations

from ..schemas.common import Finding


def correlate(findings: list[Finding]) -> list[dict]:
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file or "unknown", []).append(f)

    correlated: list[dict] = []
    for file, group in by_file.items():
        modules = {g.module for g in group}
        boost = 0
        reasons: list[str] = []
        if "dependency" in modules and "ghost_path" in modules:
            boost += 1
            reasons.append("unverified dependency coincides with weak error handling")
        if "blueprint" in modules and "reuse" in modules:
            boost += 1
            reasons.append("architecture violation coincides with possible duplication")
        if "dependency" in modules and "blueprint" in modules:
            boost += 1
            reasons.append("unverified dependency used outside expected layer")
        if boost:
            correlated.append(
                {
                    "file": file,
                    "finding_ids": [g.finding_id for g in group],
                    "priority_boost": boost,
                    "reasons": reasons,
                    "evidence_count": sum(len(g.evidence) for g in group),
                }
            )
    return correlated
