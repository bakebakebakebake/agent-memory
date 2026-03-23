from __future__ import annotations

from dataclasses import asdict

from agent_memory.client import MemoryClient
from agent_memory.config import AgentMemoryConfig


class _FallbackMCPServer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, object] = {}

    def tool(self, name: str | None = None):
        def decorator(func):
            self.tools[name or func.__name__] = func
            return func

        return decorator


def _serialize_trace(report) -> dict[str, object]:
    return {
        "focus": {"id": report.focus.id, "content": report.focus.content},
        "ancestors": [{"id": item.id, "content": item.content} for item in report.ancestors],
        "descendants": [{"id": item.id, "content": item.content} for item in report.descendants],
        "relations": [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type.value,
            }
            for edge in report.relations
        ],
        "evolution_events": report.evolution_events,
    }


def _make_server() -> object:
    try:
        from fastmcp import FastMCP

        return FastMCP("agent-memory")
    except ImportError:
        return _FallbackMCPServer("agent-memory")


def create_mcp_server(client: MemoryClient) -> object:
    server = _make_server()

    @server.tool("memory_store")
    def memory_store(content: str, source_id: str, memory_type: str = "semantic") -> dict[str, object]:
        item = client.add(content, source_id=source_id, memory_type=memory_type)  # type: ignore[arg-type]
        return {"id": item.id, "content": item.content, "trust_score": item.trust_score}

    @server.tool("memory_search")
    def memory_search(query: str, limit: int = 5) -> list[dict[str, object]]:
        return [
            {
                "id": result.item.id,
                "content": result.item.content,
                "score": result.score,
                "matched_by": result.matched_by,
            }
            for result in client.search(query, limit=limit)
        ]

    @server.tool("memory_ingest_conversation")
    def memory_ingest_conversation(turns: list[dict[str, str]], source_id: str) -> list[dict[str, object]]:
        items = client.ingest_conversation(
            [client.turn_model(**turn) for turn in turns],
            source_id=source_id,
        )
        return [{"id": item.id, "content": item.content} for item in items]

    @server.tool("memory_trace")
    def memory_trace(memory_id: str, max_depth: int = 10) -> dict[str, object]:
        return _serialize_trace(client.trace_graph(memory_id, max_depth=max_depth))

    @server.tool("memory_health")
    def memory_health() -> dict[str, object]:
        return asdict(client.health())

    @server.tool("memory_audit")
    def memory_audit(limit: int = 50) -> list[dict[str, object]]:
        return client.audit_events(limit=limit)

    @server.tool("memory_evolution")
    def memory_evolution(memory_id: str, limit: int = 50) -> list[dict[str, object]]:
        return client.evolution_events(memory_id=memory_id, limit=limit)

    @server.tool("memory_update")
    def memory_update(memory_id: str, content: str) -> dict[str, object]:
        item = client.get(memory_id)
        if item is None:
            raise ValueError(f"Memory {memory_id} not found")
        updated = client.update(item, content=content)
        return {"id": updated.id, "content": updated.content}

    @server.tool("memory_delete")
    def memory_delete(memory_id: str) -> dict[str, object]:
        return {"deleted": client.delete(memory_id)}

    @server.tool("memory_maintain")
    def memory_maintain() -> dict[str, object]:
        return asdict(client.maintain())

    @server.tool("memory_export")
    def memory_export(path: str) -> dict[str, object]:
        exported = client.export_jsonl(path)
        return {"path": path, "exported": exported}

    return server


def main() -> int:
    client = MemoryClient(config=AgentMemoryConfig.from_env())
    server = create_mcp_server(client)
    run = getattr(server, "run", None)
    if callable(run):
        run()
        return 0
    print("FastMCP is not installed. Install with `pip install -e .[mcp]`.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
