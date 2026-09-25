import asyncio


def test_direct_sql_violation():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    files = [ChangedFile(path="svc.py", added_lines=[(10, 'cursor.execute("SELECT * FROM users")')], hunks=[])]
    out = asyncio.run(blueprint.run(files, rules))
    assert len(out) == 1 and out[0].rule == "database.repository_only"


def test_valid_repo_usage_no_finding():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    files = [ChangedFile(path="svc.py", added_lines=[(1, "UserRepository.get_user(uid)")], hunks=[])]
    out = asyncio.run(blueprint.run(files, rules))
    assert out == []


def test_string_literal_pattern_not_flagged():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    files = [
        ChangedFile(
            path="blueprint.py",
            added_lines=[(1, 'PATTERNS = {"db": (["cursor.execute", "SELECT * FROM"], "Repo")}')],
            hunks=[],
        )
    ]
    out = asyncio.run(blueprint.run(files, rules))
    assert out == []


def test_real_call_reports_exact_line():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    files = [
        ChangedFile(
            path="svc.py",
            added_lines=[(5, "x = 1"), (6, 'cursor.execute("SELECT * FROM users")')],
            hunks=[],
        )
    ]
    out = asyncio.run(blueprint.run(files, rules))
    assert len(out) == 1 and out[0].line == 6


def test_docstring_example_not_flagged():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    src = '"""Real calls like\ncursor.execute("...") keep matching.\n"""\n\n\ndef ok():\n    return 1\n'
    files = [ChangedFile(path="m.py", added_lines=list(enumerate(src.splitlines(), 1)), hunks=[])]
    out = asyncio.run(blueprint.run(files, rules, {"m.py": src}))
    assert out == []


def test_comment_not_flagged():
    from src.ghost_hunter.agents.code_review import blueprint
    from src.ghost_hunter.schemas.review import ArchitectureRule, ChangedFile

    rules = [ArchitectureRule(rule_id="database.repository_only", title="DB via repo", source="ARCHITECTURE.md:1", severity="high")]
    files = [ChangedFile(path="svc.py", added_lines=[(1, "# cursor.execute is banned here")], hunks=[])]
    out = asyncio.run(blueprint.run(files, rules))
    assert out == []
