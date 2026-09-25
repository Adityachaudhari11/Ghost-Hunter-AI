def test_evidence_gate_and_correlator():
    from src.ghost_hunter.core.evidence import validate_findings
    from src.ghost_hunter.core.risk_correlator import correlate
    from src.ghost_hunter.schemas.common import Evidence, Finding, Severity

    no_ev = Finding(finding_id="GH-000", source="x", module="dependency", severity=Severity.CRITICAL, confidence=0.9, observed="o", rule="r", suggestion="s")
    assert validate_findings([no_ev]) == []
    good = Finding(finding_id="GH-000", source="dependency_agent", module="dependency", severity=Severity.CRITICAL, confidence=0.9, file="a.py", line=1, rule="pypi:x", observed="unverified", evidence=[Evidence(kind="registry_lookup", description="d", ref="pypi:x")], suggestion="verify")
    ghost = Finding(finding_id="GH-000", source="ghost_path_agent", module="ghost_path", severity=Severity.HIGH, confidence=0.9, file="a.py", line=2, rule="error_handling.no_swallow", observed="swallow", evidence=[Evidence(kind="ast_node", description="d", ref="a.py:2")], suggestion="fix")
    valid = validate_findings([good, ghost])
    assert len(valid) == 2 and valid[0].finding_id.startswith("GH-")
    corr = correlate(valid)
    assert corr and corr[0]["priority_boost"] >= 1
