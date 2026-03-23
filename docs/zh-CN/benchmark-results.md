# Benchmark 结果

[English](../benchmark-results.md) | [简体中文](benchmark-results.md)

来源脚本：`benchmarks/locomo_lite/evaluate.py`

## 最新一次运行

- 日期：`2026-03-24`
- 数据集：`30` 段对话 / `150` 个问题
- 输出文件：`benchmarks/locomo_lite/latest_results.json`

## 摘要

| 指标 | Full routing | Semantic-only |
|------|--------------|---------------|
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

## 解读

- 意图感知路由将整体命中率提升了 `+26.7pp`
- 收益最明显的类别是 `FACTUAL`、`TEMPORAL` 和 `CAUSAL`
- `NEGATIVE` 类问题在两个模式下都较容易，因为评测检查的是“不应命中”
- `PROCEDURAL` 仍然偏弱，是下一阶段最清晰的优化方向

## 复现

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```
