import json

from agent_memory.cli import main


def test_cli_store_search_and_health(tmp_path, capsys) -> None:
    db_path = tmp_path / "agent-memory.db"

    assert main(["--db", str(db_path), "store", "User prefers SQLite.", "--source-id", "cli-test"]) == 0
    stored = json.loads(capsys.readouterr().out)
    assert stored["content"] == "User prefers SQLite."

    assert main(["--db", str(db_path), "search", "SQLite"]) == 0
    search_results = json.loads(capsys.readouterr().out)
    assert search_results
    assert search_results[0]["id"] == stored["id"]

    assert main(["--db", str(db_path), "health"]) == 0
    health = json.loads(capsys.readouterr().out)
    assert health["total_memories"] == 1


def test_cli_trace_export_import_and_audit(tmp_path, capsys) -> None:
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    export_path = tmp_path / "export.jsonl"

    assert main(["--db", str(source_db), "store", "User values traceability.", "--source-id", "root"]) == 0
    root = json.loads(capsys.readouterr().out)
    assert main(
        [
            "--db",
            str(source_db),
            "store",
            "SQLite is chosen because traceability matters.",
            "--source-id",
            "child",
            "--causal-parent-id",
            root["id"],
        ]
    ) == 0
    child = json.loads(capsys.readouterr().out)

    assert main(["--db", str(source_db), "trace", root["id"]]) == 0
    trace = json.loads(capsys.readouterr().out)
    assert trace["focus"]["id"] == root["id"]
    assert trace["descendants"][0]["id"] == child["id"]

    assert main(["--db", str(source_db), "audit"]) == 0
    audit = json.loads(capsys.readouterr().out)
    assert audit

    assert main(["--db", str(source_db), "export", str(export_path)]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["exported"] == 2

    assert main(["--db", str(target_db), "import", str(export_path)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["imported"] == 2

    assert main(["--db", str(target_db), "evolution", child["id"]]) == 0
    evolution = json.loads(capsys.readouterr().out)
    assert evolution
