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


def run_storage_benchmark(num_memories: int = 1000) -> dict[str, float]:
    backend = SQLiteBackend(":memory:")
    client = MemoryClient(config=AgentMemoryConfig(database_path=":memory:"), backend=backend)
    latencies_ms: list[float] = []
    start = time.perf_counter()
    for index in range(num_memories):
        op_start = time.perf_counter()
        client.add(
            f"User preference #{index}: prefers deterministic local memory pipelines.",
            source_id="bench-storage",
            tags=["benchmark"],
        )
        latencies_ms.append((time.perf_counter() - op_start) * 1000)
    total_seconds = time.perf_counter() - start
    return {
        "num_memories": float(num_memories),
        "total_seconds": total_seconds,
        "throughput_ops_per_sec": num_memories / total_seconds,
        "avg_latency_ms": mean(latencies_ms),
        "max_latency_ms": max(latencies_ms),
    }


if __name__ == "__main__":
    print(run_storage_benchmark())
