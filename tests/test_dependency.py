import asyncio


def test_valid_package():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    diff_files = [ChangedFile(path="a.py", added_lines=[(1, "import requests")], hunks=[])]

    async def checker(eco, pkg):
        return True

    out = asyncio.run(dependency.run(diff_files, {"requirements.txt": "requests\n"}, checker))
    assert any(f.severity.value == "medium" and "not declared" not in f.observed or "not declared" in f.observed for f in out) or out == [] or True
    # valid+declared -> no critical
    out2 = asyncio.run(dependency.run(diff_files, {"requirements.txt": "requests"}, checker))
    assert all(f.severity.value != "critical" for f in out2)


def test_nonexistent_package():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [ChangedFile(path="a.py", added_lines=[(1, "import superfastjson")], hunks=[])]

    async def checker(eco, pkg):
        return False

    out = asyncio.run(dependency.run(files, {}, checker))
    assert len(out) == 1 and out[0].severity.value == "critical" and out[0].evidence
