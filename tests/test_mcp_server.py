from agent_memory.interfaces import mcp_server, rest_api
import threading


def test_mcp_server_registers_memory_tools(client, monkeypatch) -> None:
    monkeypatch.setattr(mcp_server, "_make_server", lambda: mcp_server._FallbackMCPServer("test"))
    server = mcp_server.create_mcp_server(client)

    assert set(server.tools) == {
        "memory_store",
        "memory_search",
        "memory_ingest_conversation",
        "memory_trace",
        "memory_health",
        "memory_audit",
        "memory_evolution",
        "memory_update",
        "memory_delete",
        "memory_maintain",
        "memory_export",
    }
    stored = server.tools["memory_store"]("The user prefers SQLite.", "session-1")
    results = server.tools["memory_search"]("SQLite")
    assert stored["id"] == results[0]["id"]
    trace = server.tools["memory_trace"](stored["id"])
    assert trace["focus"]["id"] == stored["id"]


def test_rest_api_fallback_exposes_routes(client, monkeypatch) -> None:
    monkeypatch.setattr(rest_api, "_make_app", lambda: rest_api._FallbackRestApp())
    app = rest_api.create_rest_app(client)

    assert "POST /memories" in app.routes
    created = app.routes["POST /memories"]({"content": "The user prefers SQLite.", "source_id": "rest"})
    found = app.routes["GET /search"]("SQLite")
    health = app.routes["GET /health"]()
    trace = app.routes["GET /trace"](created["id"])
    maintenance = app.routes["POST /maintain"]()
    assert created["id"] == found[0]["id"]
    assert "total_memories" in health
    assert trace["focus"]["id"] == created["id"]
    assert "conflicts_found" in maintenance


def test_client_health_can_run_from_another_thread(client) -> None:
    errors: list[Exception] = []
    result: dict[str, object] = {}

    def worker() -> None:
        try:
            result["health"] = client.health()
        except Exception as exc:  # pragma: no cover - regression capture
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert not errors
    assert "health" in result
