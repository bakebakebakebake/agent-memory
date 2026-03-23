# LOCOMO-Lite

This folder contains a synthetic evaluation starter set for `agent-memory`.

## Purpose

- sanity-check long-context memory retrieval
- compare full intent-aware routing against semantic-only retrieval
- provide a reproducible benchmark for README and release notes

## Files

- `sample_dialogues.jsonl` — 30 multi-turn synthetic sessions
- `sample_questions.jsonl` — 150 benchmark questions with expected answers
- `evaluate.py` — benchmark runner

## Evaluation Loop

1. ingest each dialogue into `MemoryClient`
2. run each question through `client.search()` in `full` mode
3. run the same questions through a semantic-only baseline
4. compute hit rate by intent and latency statistics

## Run

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```
