# Benchmark Results

[English](benchmark-results.md) | [简体中文](zh-CN/benchmark-results.md)

## 1. Retrieval Quality Snapshot

Source script: `benchmarks/locomo_lite/evaluate.py`

- Date: `2026-03-24`
- Dataset: `30` dialogues / `150` questions
- Output: `benchmarks/locomo_lite/latest_results.json`

| Metric | Full routing | Semantic-only |
|--------|--------------|---------------|
| Overall hit rate | 50.0% (`75/150`) | 23.3% (`35/150`) |
| Factual hit rate | 53.3% (`16/30`) | 6.7% (`2/30`) |
| Temporal hit rate | 36.7% (`11/30`) | 3.3% (`1/30`) |
| Causal hit rate | 53.3% (`16/30`) | 6.7% (`2/30`) |
| Procedural hit rate | 6.7% (`2/30`) | 0.0% (`0/30`) |
| Negative hit rate | 100.0% (`30/30`) | 100.0% (`30/30`) |

## 2. Go Native Benchmarks

Run date: `2026-03-25`

Environment:

- `darwin / arm64`
- CPU: `Apple M4`

| Benchmark | Result |
|-----------|--------|
| `BenchmarkRouterClassify` | `211.9 ns/op`, `64 B/op`, `1 allocs/op` |
| `BenchmarkReciprocalRankFusion` | `1044 ns/op`, `1296 B/op`, `11 allocs/op` |
| `BenchmarkOrchestratorSearch` | `661156 ns/op`, `213603 B/op`, `6581 allocs/op` |
| `BenchmarkAddMemory` | `40031 ns/op`, `7320 B/op`, `154 allocs/op` |
| `BenchmarkGetMemory` | `12634 ns/op`, `3833 B/op`, `129 allocs/op` |
| `BenchmarkSearchFullText` | `135832 ns/op`, `26665 B/op`, `755 allocs/op` |
| `BenchmarkSearchByVector` | `376868 ns/op`, `192908 B/op`, `5976 allocs/op` |
| `BenchmarkSearchByEntities` | `223968 ns/op`, `22221 B/op`, `686 allocs/op` |
| `BenchmarkSoftDeleteMemory` | `36848 ns/op`, `2266 B/op`, `62 allocs/op` |
| `BenchmarkTraceAncestors` | `73801 ns/op`, `16592 B/op`, `533 allocs/op` |
| `BenchmarkHealthSnapshot` | `39077 ns/op`, `2072 B/op`, `58 allocs/op` |

## 3. Go vs Python Comparison

Source script: `benchmarks/compare_go_python.py`

| Scale | Metric | Python (ms) | Go REST (ms) | Delta |
|------:|--------|------------:|-------------:|------:|
| 100 | Store | 0.24 | 0.53 | +0.30 |
| 100 | Full-text | 6.68 | 0.52 | -6.16 |
| 100 | Vector | 1.56 | 1.29 | -0.27 |
| 100 | Entity | 0.50 | 0.65 | +0.15 |
| 100 | Health | 0.08 | 0.33 | +0.25 |
| 1000 | Store | 0.26 | 0.72 | +0.46 |
| 1000 | Full-text | 242.78 | 1.20 | -241.57 |
| 1000 | Vector | 21.76 | 11.72 | -10.05 |
| 1000 | Entity | 3.92 | 3.51 | -0.41 |
| 1000 | Health | 1.16 | 0.89 | -0.27 |

## 4. Interpretation

- full routing still improves retrieval quality clearly over semantic-only retrieval
- Go service-side full-text and vector retrieval now outperform the Python embedded backend at medium scale
- Python embedded mode remains competitive on small-scale writes and simple health reads
- the next optimization target is still the Go vector-search hot path and orchestrator allocation pressure

## 5. Reproduce

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
```

```bash
cd go-server && go test -run=^$ -bench=. ./...
```

```bash
PYTHONPATH=src .venv/bin/python benchmarks/compare_go_python.py --scales 100 1000
```
