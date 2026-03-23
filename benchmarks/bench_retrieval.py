from __future__ import annotations

from pathlib import Path
from statistics import mean
import sys
import time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_memory import MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.storage.sqlite_backend import SQLiteBackend


def build_client(num_memories: int = 500) -> MemoryClient:
    backend = SQLiteBackend(":memory:")
    client = MemoryClient(config=AgentMemoryConfig(database_path=":memory:"), backend=backend)
    for index in range(num_memories):
        client.add(
            f"Project note {index}: SQLite, MCP, trust scoring, and traceability are important.",
            source_id="bench-retrieval",
            tags=["benchmark", "memory"],
        )
    return client


def run_retrieval_benchmark(iterations: int = 100, num_memories: int = 500) -> dict[str, float]:
    client = build_client(num_memories=num_memories)
    latencies_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        client.search("Why does the project prefer SQLite and traceability?", limit=5)
        latencies_ms.append((time.perf_counter() - start) * 1000)
    latencies_ms.sort()
    return {
        "iterations": float(iterations),
        "num_memories": float(num_memories),
        "avg_latency_ms": mean(latencies_ms),
        "p50_latency_ms": latencies_ms[int(len(latencies_ms) * 0.5)],
        "p95_latency_ms": latencies_ms[int(len(latencies_ms) * 0.95)],
        "p99_latency_ms": latencies_ms[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.99))],
    }


if __name__ == "__main__":
    print(run_retrieval_benchmark())
