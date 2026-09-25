import asyncio


def test_duplicate_and_unrelated():
    from src.ghost_hunter.agents.code_review import reuse
    from src.ghost_hunter.schemas.review import ChangedFile

    existing = [{"name": "format_timestamp", "file": "DateUtils.py", "line": 1, "code": "def format_timestamp(ts):\n    return str(ts)"}]
    new_dup = "def format_date(timestamp):\n    return str(timestamp)\n"
    files = [ChangedFile(path="new.py", added_lines=[(1, l) for l in new_dup.splitlines()], hunks=[])]
    out = asyncio.run(reuse.run(files, {"new.py": new_dup}, existing))
    assert any("duplicate" in f.observed.lower() for f in out)

    new_other = "def launch_rocket(x):\n    return x * 999 + orbit()\n"
    files2 = [ChangedFile(path="new.py", added_lines=[(1, l) for l in new_other.splitlines()], hunks=[])]
    out2 = asyncio.run(reuse.run(files2, {"new.py": new_other}, existing))
    assert out2 == []
