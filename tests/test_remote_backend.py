from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import subprocess
import time
from types import SimpleNamespace

from agent_memory.client import MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.models import MemoryItem, MemoryType
from agent_memory.storage.remote_backend import RemoteBackend


class DummyEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float(index + 1), float(len(text))] for index, text in enumerate(texts)]


def test_config_loads_remote_mode(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MEMORY_MODE", "remote")
    monkeypatch.setenv("AGENT_MEMORY_GO_SERVER_URL", "http://localhost:18080")
    monkeypatch.setenv("AGENT_MEMORY_GRPC_TARGET", "localhost:19090")
    monkeypatch.setenv("AGENT_MEMORY_PREFER_GRPC", "false")

    config = AgentMemoryConfig.from_env()

    assert config.mode == "remote"
    assert config.go_server_url == "http://localhost:18080"
    assert config.grpc_target == "localhost:19090"
    assert config.prefer_grpc is False


def test_client_builds_remote_backend(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MEMORY_MODE", "remote")
    client = MemoryClient(config=AgentMemoryConfig.from_env(), embedding_provider=DummyEmbeddingProvider())
    try:
        assert isinstance(client.backend, RemoteBackend)
    finally:
        client.close()


def test_client_remote_search_uses_go_path(monkeypatch) -> None:
    backend = RemoteBackend(
        AgentMemoryConfig(
            mode="remote",
            go_server_url="http://localhost:18080",
            grpc_target="localhost:19090",
            prefer_grpc=False,
        )
    )
    called = {"search_query": False}

    def fake_search_query(query: str, *, embedding: list[float], entities: list[str], limit: int = 5):
        called["search_query"] = True
        return []

    monkeypatch.setattr(backend, "search_query", fake_search_query)
    client = MemoryClient(
        config=AgentMemoryConfig(mode="remote", prefer_grpc=False),
        backend=backend,
        embedding_provider=DummyEmbeddingProvider(),
    )
    try:
        assert client.search("SQLite", limit=3) == []
        assert called["search_query"] is True
    finally:
        client.close()


def test_remote_backend_parses_http_payload(monkeypatch) -> None:
    backend = RemoteBackend(
        AgentMemoryConfig(
            mode="remote",
            go_server_url="http://localhost:18080",
            grpc_target="localhost:19090",
            prefer_grpc=False,
        )
    )

    def fake_request_json(method: str, path: str, *, data=None):
        if path == "/health":
            return {
                "total_memories": 3,
                "stale_ratio": 0.1,
                "orphan_ratio": 0.0,
                "unresolved_conflicts": 1,
                "average_trust_score": 0.8,
                "audit_events": 5,
                "database_size_bytes": 1024,
            }
        return {
            "results": [
                {
                    "item": {
                        "id": "m1",
                        "content": "SQLite works well for agents.",
                        "memory_type": "semantic",
                        "embedding": [0.1, 0.2, 0.3],
                        "created_at": "2026-03-25T00:00:00+00:00",
                        "last_accessed": "2026-03-25T00:00:00+00:00",
                        "access_count": 0,
                        "trust_score": 0.75,
                        "importance": 0.5,
                        "layer": "short_term",
                        "decay_rate": 0.1,
                        "source_id": "test",
                        "entity_refs": ["sqlite"],
                        "tags": ["db"],
                    },
                    "score": 0.9,
                }
            ]
        }

    monkeypatch.setattr(backend, "_request_json", fake_request_json)

    results = backend.search_full_text("SQLite", limit=5)
    health = backend.health_snapshot()

    assert results[0][0].id == "m1"
    assert results[0][1] == 0.9
    assert health["total_memories"] == 3


def test_remote_backend_relation_exists_uses_grpc_bool_value() -> None:
    backend = RemoteBackend(
        AgentMemoryConfig(
            mode="remote",
            go_server_url="http://localhost:18080",
            grpc_target="localhost:19090",
            prefer_grpc=True,
        )
    )
    backend._grpc_stub = object()

    def fake_grpc_call(method: str, request):
        assert method == "RelationExists"
        assert request.left_id == "left"
        assert request.right_id == "right"
        assert list(request.relation_types) == ["contradicts"]
        return SimpleNamespace(value=True)

    backend._grpc_call = fake_grpc_call  # type: ignore[method-assign]

    assert backend.relation_exists_between("left", "right", ["contradicts"]) is True


def test_remote_backend_uses_grpc_with_go_server(tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    go_server_dir = project_root / "go-server"
    db_path = tmp_path / "grpc-test.db"
    http_port = _find_free_port()
    grpc_port = _find_free_port(exclude={http_port})
    env = os.environ.copy()
    env.update(
        {
            "AGENT_MEMORY_DATABASE_PATH": str(db_path),
            "AGENT_MEMORY_HTTP_ADDRESS": f"127.0.0.1:{http_port}",
            "AGENT_MEMORY_GRPC_ADDRESS": f"127.0.0.1:{grpc_port}",
            "AGENT_MEMORY_API_KEY": "grpc-test-key",
        }
    )
    process = subprocess.Popen(
        ["go", "run", "./cmd/server"],
        cwd=go_server_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_port("127.0.0.1", grpc_port, process=process)
        backend = RemoteBackend(
            AgentMemoryConfig(
                mode="remote",
                go_server_url=f"http://127.0.0.1:{http_port}",
                grpc_target=f"127.0.0.1:{grpc_port}",
                prefer_grpc=True,
                api_key="grpc-test-key",
            )
        )
        now = datetime.now(timezone.utc)
        item = MemoryItem(
            id="grpc-py-1",
            content="gRPC bridge works for Python remote backend.",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.2, 0.3],
            created_at=now,
            last_accessed=now,
            source_id="pytest",
            entity_refs=["grpc"],
            tags=["remote"],
        )
        stored = backend.add_memory(item)
        found = backend.get_memory(stored.id)
        search_results = backend.search_query(
            "grpc bridge",
            embedding=[0.1, 0.2, 0.3],
            entities=["grpc"],
            limit=5,
        )
        health = backend.health_snapshot()
        backend.close()

        assert found is not None
        assert found.content == item.content
        assert search_results
        assert search_results[0].item.id == stored.id
        assert health["total_memories"] >= 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def _wait_for_port(host: str, port: int, timeout: float = 20.0, process: subprocess.Popen[str] | None = None) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            if process is not None and process.poll() is not None:
                output = ""
                if process.stdout is not None:
                    output = process.stdout.read()
                raise AssertionError(f"Go server exited before port {host}:{port} was ready:\n{output}")
            time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for {host}:{port}")


def _find_free_port(*, exclude: set[int] | None = None) -> int:
    blocked = exclude or set()
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = int(sock.getsockname()[1])
        if port not in blocked:
            return port
