from benchmarks.bench_retrieval import run_retrieval_benchmark
from benchmarks.bench_storage import run_storage_benchmark


def test_storage_benchmark_smoke() -> None:
    metrics = run_storage_benchmark(num_memories=10)
    assert metrics["throughput_ops_per_sec"] > 0
    assert metrics["avg_latency_ms"] >= 0


def test_retrieval_benchmark_smoke() -> None:
    metrics = run_retrieval_benchmark(iterations=5, num_memories=20)
    assert metrics["p50_latency_ms"] >= 0
    assert metrics["p95_latency_ms"] >= metrics["p50_latency_ms"]

