from __future__ import annotations

from dataclasses import asdict

from agent_memory.client import MemoryClient
from agent_memory.interfaces.mcp_server import _serialize_trace


class _FallbackRestApp:
    def __init__(self) -> None:
        self.routes: dict[str, object] = {}

    def add_api_route(self, path: str, endpoint, methods: list[str]) -> None:
        for method in methods:
            self.routes[f"{method.upper()} {path}"] = endpoint


def _make_app() -> object:
    try:
        from fastapi import FastAPI

        return FastAPI(title="agent-memory")
    except ImportError:
        return _FallbackRestApp()


def create_rest_app(client: MemoryClient) -> object:
    app = _make_app()

    def create_memory(payload: dict[str, object]) -> dict[str, object]:
        item = client.add(
            str(payload["content"]),
            source_id=str(payload.get("source_id", "rest")),
            memory_type=str(payload.get("memory_type", "semantic")),  # type: ignore[arg-type]
        )
        return {"id": item.id, "content": item.content}

    def search_memory(query: str, limit: int = 5) -> list[dict[str, object]]:
        return [
            {"id": result.item.id, "content": result.item.content, "score": result.score}
            for result in client.search(query, limit=limit)
        ]

    def read_health() -> dict[str, object]:
        return asdict(client.health())

    def read_audit(limit: int = 50) -> list[dict[str, object]]:
        return client.audit_events(limit=limit)

    def read_evolution(memory_id: str, limit: int = 50) -> list[dict[str, object]]:
        return client.evolution_events(memory_id=memory_id, limit=limit)

    def trace_memory(memory_id: str, max_depth: int = 10) -> dict[str, object]:
        return _serialize_trace(client.trace_graph(memory_id, max_depth=max_depth))

    def run_maintenance() -> dict[str, object]:
        return asdict(client.maintain())

    def export_memory(path: str) -> dict[str, object]:
        exported = client.export_jsonl(path)
        return {"path": path, "exported": exported}

    app.add_api_route("/memories", create_memory, methods=["POST"])
    app.add_api_route("/search", search_memory, methods=["GET"])
    app.add_api_route("/health", read_health, methods=["GET"])
    app.add_api_route("/audit", read_audit, methods=["GET"])
    app.add_api_route("/evolution", read_evolution, methods=["GET"])
    app.add_api_route("/trace", trace_memory, methods=["GET"])
    app.add_api_route("/maintain", run_maintenance, methods=["POST"])
    app.add_api_route("/export", export_memory, methods=["POST"])
    return app
