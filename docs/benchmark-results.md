# Benchmark Results

[English](benchmark-results.md) | [简体中文](zh-CN/benchmark-results.md)

Source script: `benchmarks/locomo_lite/evaluate.py`

## Latest Run

- Date: `2026-03-24`
- Dataset: `30` dialogues / `150` questions
- Output artifact: `benchmarks/locomo_lite/latest_results.json`

## Summary

| Metric | Full routing | Semantic-only |
|--------|--------------|---------------|
| Overall hit rate | 50.0% (`75/150`) | 23.3% (`35/150`) |
| Factual hit rate | 53.3% (`16/30`) | 6.7% (`2/30`) |
| Temporal hit rate | 36.7% (`11/30`) | 3.3% (`1/30`) |
| Causal hit rate | 53.3% (`16/30`) | 6.7% (`2/30`) |
| Procedural hit rate | 6.7% (`2/30`) | 0.0% (`0/30`) |
| Negative hit rate | 100.0% (`30/30`) | 100.0% (`30/30`) |
| p50 latency | 12.72ms | 10.85ms |
| p95 latency | 16.64ms | 11.50ms |
| p99 latency | 17.25ms | 13.24ms |
| Embedding calls | 232 | 232 |

## Interpretation

- Intent-aware routing improves overall hit rate by `+26.7pp`.
- Gains are strongest on `FACTUAL`, `TEMPORAL`, and `CAUSAL` questions.
- `NEGATIVE` questions are easy for both modes because the benchmark checks absence.
- `PROCEDURAL` recall remains weak and is the clearest next optimization target.

## Reproduce

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```
