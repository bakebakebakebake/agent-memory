from __future__ import annotations

import argparse
import contextlib
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Callable
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent_memory.models import MemoryItem, MemoryType
from agent_memory.storage.sqlite_backend import SQLiteBackend


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def generate_items(count: int, prefix: str) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    now = utc_now()
    for index in range(count):
        items.append(
            MemoryItem(
                id=f"{prefix}-{index}",
                content=f"SQLite keeps agent memory local and traceable {index}",
                memory_type=MemoryType.SEMANTIC,
                embedding=[0.1 + (index % 5) * 0.01, 0.2, 0.3],
                created_at=now,
                last_accessed=now,
                trust_score=0.8,
                importance=0.6,
                source_id="bench-compare",
                entity_refs=["sqlite", "agent"],
                tags=["benchmark", "compare"],
            )
        )
    return items


def to_payload(item: MemoryItem) -> dict[str, object]:
    payload = asdict(item)
    payload["memory_type"] = item.memory_type.value
    payload["layer"] = item.layer.value
    payload["created_at"] = item.created_at.isoformat()
    payload["last_accessed"] = item.last_accessed.isoformat()
    payload["valid_from"] = item.valid_from.isoformat() if item.valid_from else None
    payload["valid_until"] = item.valid_until.isoformat() if item.valid_until else None
    payload["deleted_at"] = item.deleted_at.isoformat() if item.deleted_at else None
    return payload


def measure(runs: int, func: Callable[[], None]) -> float:
    started = time.perf_counter()
    for _ in range(runs):
        func()
    elapsed = time.perf_counter() - started
    return elapsed * 1000 / runs


def post_json(base_url: str, path: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(base_url: str, path: str) -> dict[str, object]:
    with request.urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_server(base_url: str, timeout_seconds: float = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            get_json(base_url, "/health")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Go server did not become ready at {base_url}")


def start_go_server(db_path: Path) -> tuple[subprocess.Popen[str], str]:
    http_port = free_port()
    grpc_port = free_port()
    base_url = f"http://127.0.0.1:{http_port}"
    env = os.environ.copy()
    env.update(
        {
            "AGENT_MEMORY_HTTP_ADDRESS": f"127.0.0.1:{http_port}",
            "AGENT_MEMORY_GRPC_ADDRESS": f"127.0.0.1:{grpc_port}",
            "AGENT_MEMORY_DATABASE_PATH": str(db_path),
            "AGENT_MEMORY_REQUEST_TIMEOUT_SECONDS": "10",
        }
    )
    process = subprocess.Popen(
        ["go", "run", "./cmd/server"],
        cwd=REPO_ROOT / "go-server",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    wait_for_server(base_url)
    return process, base_url


def stop_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def compare_scale(scale: int) -> dict[str, float]:
    python_db = Path(tempfile.mkdtemp(prefix="agent-memory-python-")) / "memory.db"
    python_items = generate_items(scale, f"python-scale-{scale}")
    python_backend = SQLiteBackend(str(python_db), prefer_sqlite_vec=False)
    try:
        python_store_pool = list(generate_items(scale, f"python-store-{scale}"))
        python_store_ms = measure(len(python_store_pool), lambda: python_backend.add_memory(python_store_pool.pop(0)))
        for item in python_items:
            python_backend.add_memory(item)
        python_full_text_ms = measure(5, lambda: python_backend.search_full_text("SQLite agent", limit=5))
        python_vector_ms = measure(5, lambda: python_backend.search_by_vector([0.1, 0.2, 0.3], limit=5))
        python_entity_ms = measure(5, lambda: python_backend.search_by_entities(["sqlite", "agent"], limit=5))
        python_health_ms = measure(5, lambda: python_backend.health_snapshot())
    finally:
        python_backend.close()

    go_db = Path(tempfile.mkdtemp(prefix="agent-memory-go-")) / "memory.db"
    process, base_url = start_go_server(go_db)
    try:
        go_store_pool = list(generate_items(scale, f"go-store-{scale}"))
        go_store_ms = measure(len(go_store_pool), lambda: post_json(base_url, "/api/v1/memories", to_payload(go_store_pool.pop(0))))
        go_items = generate_items(scale, f"go-scale-{scale}")
        for item in go_items:
            post_json(base_url, "/api/v1/memories", to_payload(item))
        go_full_text_ms = measure(
            5,
            lambda: post_json(base_url, "/api/v1/search/full-text", {"query": "SQLite agent", "limit": 5, "memory_type": ""}),
        )
        go_vector_ms = measure(
            5,
            lambda: post_json(base_url, "/api/v1/search/vector", {"embedding": [0.1, 0.2, 0.3], "limit": 5, "memory_type": ""}),
        )
        go_entity_ms = measure(
            5,
            lambda: post_json(base_url, "/api/v1/search/entities", {"entities": ["sqlite", "agent"], "limit": 5, "memory_type": ""}),
        )
        go_health_ms = measure(5, lambda: get_json(base_url, "/health"))
    finally:
        stop_process(process)

    return {
        "python_store_ms": python_store_ms,
        "python_full_text_ms": python_full_text_ms,
        "python_vector_ms": python_vector_ms,
        "python_entity_ms": python_entity_ms,
        "python_health_ms": python_health_ms,
        "go_store_ms": go_store_ms,
        "go_full_text_ms": go_full_text_ms,
        "go_vector_ms": go_vector_ms,
        "go_entity_ms": go_entity_ms,
        "go_health_ms": go_health_ms,
    }


def format_table(results: dict[int, dict[str, float]]) -> str:
    lines = [
        "| Scale | Metric | Python (ms) | Go REST (ms) | Delta |",
        "|------:|--------|------------:|-------------:|------:|",
    ]
    metrics = [
        ("Store", "python_store_ms", "go_store_ms"),
        ("Full-text", "python_full_text_ms", "go_full_text_ms"),
        ("Vector", "python_vector_ms", "go_vector_ms"),
        ("Entity", "python_entity_ms", "go_entity_ms"),
        ("Health", "python_health_ms", "go_health_ms"),
    ]
    for scale, values in results.items():
        for label, python_key, go_key in metrics:
            delta = values[go_key] - values[python_key]
            lines.append(
                f"| {scale} | {label} | {values[python_key]:.2f} | {values[go_key]:.2f} | {delta:+.2f} |"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Python embedded backend and Go REST service latency.")
    parser.add_argument("--scales", nargs="+", type=int, default=[100, 1000, 10000], help="Memory counts to compare.")
    args = parser.parse_args()

    results: dict[int, dict[str, float]] = {}
    for scale in args.scales:
        results[scale] = compare_scale(scale)

    print(format_table(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
