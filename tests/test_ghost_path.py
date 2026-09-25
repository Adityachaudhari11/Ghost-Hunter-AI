import asyncio


def test_swallowed_exception():
    from src.ghost_hunter.agents.code_review import ghost_path

    src = "def f():\n    try:\n        process_payment()\n    except Exception:\n        pass\n"
    out = ghost_path.analyze_python_source(src, "payment_service.py")
    assert any("ignored" in f.observed for f in out)


def test_proper_handling_no_finding():
    from src.ghost_hunter.agents.code_review import ghost_path

    src = "def f():\n    try:\n        x()\n    except ValueError as e:\n        logger.error(str(e))\n        raise\n"
    out = ghost_path.analyze_python_source(src, "a.py")
    assert out == []


def test_fallback_and_notimpl():
    from src.ghost_hunter.agents.code_review import ghost_path
    from src.ghost_hunter.schemas.review import ChangedFile

    files = [ChangedFile(path="a.py", added_lines=[(1, "except Exception:"), (2, "    return {}")], hunks=[])]
    out = asyncio.run(ghost_path.run(files))
    assert any("fallback" in f.observed for f in out)
