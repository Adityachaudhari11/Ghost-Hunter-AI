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
