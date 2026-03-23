from pathlib import Path

from agent_memory.interfaces import mcp_server, rest_api


def test_mcp_observability_tools(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mcp_server, "_make_server", lambda: mcp_server._FallbackMCPServer("test"))
    server = mcp_server.create_mcp_server(client)
    stored = server.tools["memory_store"]("User prefers SQLite.", "session-1")

    audit = server.tools["memory_audit"]()
    evolution = server.tools["memory_evolution"](stored["id"])
    exported = server.tools["memory_export"](str(tmp_path / "export.jsonl"))

    assert audit
    assert evolution
    assert Path(exported["path"]).exists()


def test_rest_observability_routes(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rest_api, "_make_app", lambda: rest_api._FallbackRestApp())
    app = rest_api.create_rest_app(client)

    created = app.routes["POST /memories"]({"content": "User prefers SQLite.", "source_id": "rest"})
    audit = app.routes["GET /audit"]()
    evolution = app.routes["GET /evolution"](created["id"])
    exported = app.routes["POST /export"](str(tmp_path / "rest-export.jsonl"))

    assert audit
    assert evolution
    assert Path(exported["path"]).exists()
