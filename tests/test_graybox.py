import asyncio
from pathlib import Path


def _write_repo(root: Path) -> None:
    (root / "ARCHITECTURE.md").write_text(
        "All database operations must go through the Repository layer.\n", encoding="utf-8"
    )
    (root / "bad.py").write_text(
        "import superfastjson\n"
        "\n"
        "def get_user(user_id):\n"
        "    try:\n"
        '        cursor.execute("SELECT * FROM users")\n'
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )


def test_prove_repo_finds_hallucination_and_unwanted_code(tmp_path):
    from src.ghost_hunter.testing.graybox import prove_repo

    _write_repo(tmp_path)

    async def checker(eco, pkg):
        return False if pkg == "superfastjson" else True

    report = asyncio.run(prove_repo(tmp_path, checker))
    modules = {f.module for f in report.findings}
    assert {"dependency", "blueprint", "ghost_path"} <= modules
    assert all(f.evidence for f in report.findings)
    assert report.summary["files_scanned"] >= 1
    assert report.summary["method"] == "graybox-full-repo"


def test_prove_clean_repo_is_quiet(tmp_path):
    from src.ghost_hunter.testing.graybox import prove_repo

    (tmp_path / "ok.py").write_text("import os\n\n\ndef f():\n    return os.name\n", encoding="utf-8")

    async def checker(eco, pkg):
        raise AssertionError("no external imports, registry must not be hit")

    report = asyncio.run(prove_repo(tmp_path, checker))
    assert report.findings == []


def test_github_url_parsing():
    from src.ghost_hunter.ingesters.github_repo import parse_github_url

    assert parse_github_url("https://github.com/Adityachaudhari11/Ghost-Hunter-AI")["branch"] is None
    info = parse_github_url("https://github.com/org/repo/tree/main")
    assert (info["org"], info["repo"], info["branch"]) == ("org", "repo", "main")
    for bad in (
        "https://github.com/org/repo/pull/2016",
        "https://gitlab.com/org/repo",
        "not-a-url",
    ):
        try:
            parse_github_url(bad)
        except ValueError:
            continue
        raise AssertionError(f"should reject: {bad}")
