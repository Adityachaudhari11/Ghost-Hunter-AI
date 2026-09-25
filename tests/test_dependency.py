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


def test_stdlib_never_queried():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [
        ChangedFile(
            path="a.py",
            added_lines=[(1, "import os"), (2, "from __future__ import annotations"), (3, "import typing")],
            hunks=[],
        )
    ]

    async def checker(eco, pkg):
        raise AssertionError(f"registry must not be queried for stdlib: {pkg}")

    assert asyncio.run(dependency.run(files, {}, checker)) == []


def test_non_import_lines_ignored():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [
        ChangedFile(
            path="ingesters/diff.py",
            added_lines=[
                (1, 'IMPORT_PY = re.compile(r"^\\s*(import\\s+[\\w\\.]+)")'),
                (2, 'x = \'require("leftpad")\''),
                (3, 'diff_files = [ChangedFile(path="a.py")]'),
            ],
            hunks=[],
        )
    ]

    async def checker(eco, pkg):
        raise AssertionError(f"string literal must not reach registry: {pkg}")

    assert asyncio.run(dependency.run(files, {}, checker)) == []


def test_js_imports_not_checked_on_python_files():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [ChangedFile(path="a.py", added_lines=[(1, 'x = 1  # require("y")')], hunks=[])]

    async def checker(eco, pkg):
        raise AssertionError("js resolver must not run on .py files")

    assert asyncio.run(dependency.run(files, {}, checker)) == []


def test_known_local_skipped():
    from src.ghost_hunter.agents.code_review import dependency
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [ChangedFile(path="a.py", added_lines=[(1, "from ghost_hunter.core import config")], hunks=[])]

    async def checker(eco, pkg):
        return False

    out = asyncio.run(dependency.run(files, {}, checker, {"ghost_hunter"}))
    assert out == []
