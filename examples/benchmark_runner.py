from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarks.bench_retrieval import run_retrieval_benchmark
from benchmarks.bench_storage import run_storage_benchmark


print("storage:", run_storage_benchmark(300))
print("retrieval:", run_retrieval_benchmark(iterations=50, num_memories=300))
