"""Pre-recorded demo data so ``--demo`` works with zero network calls."""

DEMO_TARGET = {
    "name": "ai-pricing-service",
    "language": "Python + TypeScript",
    "files_scanned": 14,
}

DEMO_FINDINGS = [
    {
        "id": "HALLU-01", "scanner": "hallucination", "severity": 10,
        "file": "src/pricing_ai.py", "line": 3, "package": "requests_fastly",
        "verdict": "hallucinated",
        "message": "\U0001f534 Warning: Likely AI Hallucination. High risk of supply "
                   "chain attack. `requests_fastly` does not exist on PyPI.",
        "fix": "Remove the import or replace with `requests`. Verify on pypi.org.",
    },
    {
        "id": "HALLU-02", "scanner": "hallucination", "severity": 8,
        "file": "src/cart.ts", "line": 1, "package": "lodahs",
        "verdict": "possible_typosquat",
        "message": "\U0001f6a8 Possible typosquat: `lodahs` looks like `lodash`. "
                   "Classic slop-squatting vector.",
        "fix": "Did you mean `lodash`? Pin the exact version.",
    },
    {
        "id": "BLUE-01", "scanner": "blueprint", "rule": "RAW_SQL", "severity": 8,
        "file": "src/pricing_ai.py", "line": 22,
        "message": "\U0001f7e0 [RAW_SQL] Raw SQL instead of ORM wrapper: raw SQL string "
                   "— use the designated ORM wrapper (db.query / repository layer).",
        "code": 'cursor.execute(f"SELECT * FROM prices WHERE id = {pid}")',
        "fix": "Move the query into the repository/ORM layer with parameterised bindings.",
    },
    {
        "id": "BLUE-02", "scanner": "blueprint", "rule": "CUSTOM_TIME", "severity": 6,
        "file": "src/pricing_ai.py", "line": 31,
        "message": "\U0001f7e0 [CUSTOM_TIME] Reinvented timestamp formatter: hand-rolled "
                   "timestamp formatting — use the internal format_timestamp helper.",
        "code": 'label = datetime.now().strftime("%Y-%m-%d %H:%M")',
        "fix": "Replace with format_timestamp(dt) from utils/time.",
    },
    {
        "id": "GHOST-01", "scanner": "ghostpath", "severity": 8,
        "file": "src/pricing_ai.py", "line": 40,
        "message": "\U0001f47b Ghost path [swallowed exception (pass)] — "
                   "except Exception at line 40 hides failures.",
        "code": "except Exception: pass",
        "fix": "Log the error (logger.exception) and return an explicit error value.",
    },
    {
        "id": "GHOST-02", "scanner": "ghostpath", "severity": 5,
        "file": "src/cart.ts", "line": 18,
        "message": "\U0001f47b Ghost path [unimplemented failure handling] — "
                   "placeholder left in code.",
        "code": "// TODO: handle failure scenario — retry payment later",
        "fix": "Implement the failure branch at least minimally (log + safe default).",
    },
]
