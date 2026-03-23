from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
from statistics import mean
import sys
import time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent_memory import ConversationTurn, MemoryClient
from agent_memory.config import AgentMemoryConfig


ROOT = Path(__file__).resolve().parent
DIALOGUES_PATH = ROOT / "sample_dialogues.jsonl"
QUESTIONS_PATH = ROOT / "sample_questions.jsonl"
RESULTS_PATH = ROOT / "latest_results.json"


@dataclass(slots=True)
class EvalResult:
    mode: str
    total: int
    hits: int
    by_intent: dict[str, dict[str, int]]
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    embedding_calls: int


class CountingEmbeddingProvider:
    def __init__(self, provider) -> None:
        self.provider = provider
        self.calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += len(texts)
        return self.provider.embed(texts)


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_client(mode: str) -> MemoryClient:
    client = MemoryClient(config=AgentMemoryConfig(database_path=":memory:"))
    client.embedding_provider = CountingEmbeddingProvider(client.embedding_provider)
    return client


def ingest_dialogues(client: MemoryClient, dialogues: list[dict]) -> None:
    for dialogue in dialogues:
        turns = [ConversationTurn(role=turn["role"], content=turn["content"]) for turn in dialogue["turns"]]
        client.ingest_conversation(turns, source_id=dialogue["dialogue_id"])


def semantic_only_search(client: MemoryClient, query: str, limit: int = 5):
    embedding = client.embedding_provider.embed([query])[0]
    semantic_results = client.backend.search_by_vector(embedding, limit=limit)
    output = []
    for item, score in semantic_results:
        output.append({"content": item.content, "score": score})
    return output


def full_search(client: MemoryClient, query: str, limit: int = 5):
    return [{"content": result.item.content, "score": result.score} for result in client.search(query, limit=limit)]


def is_hit(question: dict, results: list[dict]) -> bool:
    joined = " ".join(result["content"] for result in results).lower()
    expected_keywords = [keyword.lower() for keyword in question.get("expected_keywords", [])]
    if question["intent_type"] == "NEGATIVE":
        topic = question.get("negative_topic", "").lower()
        return topic not in joined
    return all(keyword in joined for keyword in expected_keywords)


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, int(len(values) * ratio))
    return values[index]


def evaluate(mode: str) -> EvalResult:
    dialogues = load_jsonl(DIALOGUES_PATH)
    questions = load_jsonl(QUESTIONS_PATH)
    client = build_client(mode)
    ingest_dialogues(client, dialogues)

    latencies_ms: list[float] = []
    by_intent_hits: dict[str, int] = defaultdict(int)
    by_intent_total: dict[str, int] = defaultdict(int)
    hits = 0

    for question in questions:
        start = time.perf_counter()
        if mode == "semantic_only":
            results = semantic_only_search(client, question["question"], limit=5)
        else:
            results = full_search(client, question["question"], limit=5)
        latencies_ms.append((time.perf_counter() - start) * 1000)
        by_intent_total[question["intent_type"]] += 1
        if is_hit(question, results):
            hits += 1
            by_intent_hits[question["intent_type"]] += 1

    latencies_ms.sort()
    by_intent = {
        intent: {"hits": by_intent_hits[intent], "total": total}
        for intent, total in sorted(by_intent_total.items())
    }
    return EvalResult(
        mode=mode,
        total=len(questions),
        hits=hits,
        by_intent=by_intent,
        avg_latency_ms=mean(latencies_ms),
        p50_latency_ms=percentile(latencies_ms, 0.5),
        p95_latency_ms=percentile(latencies_ms, 0.95),
        p99_latency_ms=percentile(latencies_ms, 0.99),
        embedding_calls=client.embedding_provider.calls,
    )


def render_report(full: EvalResult, baseline: EvalResult) -> str:
    def ratio(result: EvalResult) -> float:
        return (result.hits / result.total) * 100 if result.total else 0.0

    lines = [
        "=== LOCOMO-Lite Evaluation Report ===",
        f"Dataset: {len(load_jsonl(DIALOGUES_PATH))} dialogues, {len(load_jsonl(QUESTIONS_PATH))} questions",
        "Mode: full (intent-aware routing + RRF)",
        "",
        f"Overall hit rate:     {ratio(full):.1f}%  ({full.hits}/{full.total})",
    ]
    for intent, stats in full.by_intent.items():
        hit_rate = (stats['hits'] / stats['total']) * 100 if stats["total"] else 0.0
        lines.append(f"  {intent}:".ljust(22) + f"{hit_rate:5.1f}%  ({stats['hits']}/{stats['total']})")
    lines.extend(
        [
            "",
            f"Baseline (semantic-only): {ratio(baseline):.1f}%  ({baseline.hits}/{baseline.total})",
            f"Improvement:             {ratio(full) - ratio(baseline):+.1f}pp",
            "",
            "Retrieval latency:",
            f"  p50: {full.p50_latency_ms:.2f}ms  p95: {full.p95_latency_ms:.2f}ms  p99: {full.p99_latency_ms:.2f}ms",
            f"Embedding calls: {full.embedding_calls}",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    full = evaluate("full")
    baseline = evaluate("semantic_only")
    report = render_report(full, baseline)
    print(report)
    output = {
        "full": asdict(full),
        "semantic_only": asdict(baseline),
        "report": report,
    }
    RESULTS_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nJSON:")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\nSaved JSON report to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
