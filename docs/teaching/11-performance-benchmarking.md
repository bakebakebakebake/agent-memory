# 11 性能与基准测试
> 结合 Go 基准、Python 对比脚本和 k6 压测脚本，建立一套可复现的性能评估口径。

## 前置知识

- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)

## 本文目标

完成阅读后，你将理解：

1. 当前项目已经有哪些性能测试资产
2. Go 原生 benchmark 的最新结果是什么
3. Go 服务与 Python 嵌入后端在小规模和中规模数据上的差异
4. k6 脚本适合回答什么问题

## 基准测试哲学

本项目尽量让性能测试满足三点：

- **可复现**：命令固定，数据规模可控
- **自动化**：通过 benchmark / script / k6 直接运行
- **可解释**：每条结果都能映射到具体模块

## Go 原生基准

本次新增的基准包括：

- `BenchmarkAddMemory`
- `BenchmarkGetMemory`
- `BenchmarkSearchFullText`
- `BenchmarkSearchByVector`
- `BenchmarkSearchByEntities`
- `BenchmarkSoftDeleteMemory`
- `BenchmarkTraceAncestors`
- `BenchmarkHealthSnapshot`
- `BenchmarkOrchestratorSearch`
- `BenchmarkRouterClassify`
- `BenchmarkReciprocalRankFusion`

### 最新结果

测试环境：

- 日期：`2026-03-25`
- 系统：`darwin / arm64`
- CPU：`Apple M4`

| Benchmark | 结果 |
|-----------|------|
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

## Go vs Python 对比

对比脚本：**`benchmarks/compare_go_python.py`**

运行命令：

```bash
PYTHONPATH=src .venv/bin/python benchmarks/compare_go_python.py --scales 100 1000
```

### 最新结果

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

### 结果解读

- 写入路径上，Python 嵌入后端在当前量级仍然更轻
- 全文检索上，Go 服务层当前明显更快
- 向量检索在 `1000` 规模时，Go 侧也有优势
- 健康检查和实体查询在不同规模下差异不大

## LOCOMO-Lite 评估

仓库仍保留 Python 侧的 LOCOMO-Lite 风格评估：

- 脚本：`benchmarks/locomo_lite/evaluate.py`
- 最新结果：`benchmarks/locomo_lite/latest_results.json`

这类评估回答的是“检索质量”，和本文的“系统性能”是两条不同维度。

## k6 负载测试

本次新增：

- `benchmarks/k6/http-load.js`
- `benchmarks/k6/grpc-load.js`
- `benchmarks/k6/README.md`

它们更适合回答：

- 多并发下服务是否稳定
- p95 / p99 延迟如何变化
- HTTP 与 gRPC 哪条链路更适合当前负载

## 当前瓶颈观察

从最新结果看，当前更值得关注的点有：

- Go 向量检索仍是纯余弦扫描，数据规模再上去后成本会继续抬升
- 编排器分配次数较多，后续可继续优化中间结构
- Python FTS 在 1000 规模下延迟上升较快

## 小结

- 项目已经具备 Go benchmark、Python 对比脚本和 k6 压测三类性能资产
- 当前 Go 服务在全文检索和中等规模向量检索上有明显优势
- Python 嵌入模式在小规模写入上仍然非常轻量
- 若要继续优化，优先看向量检索和编排器分配

## 延伸阅读

- [07 数据库与 Schema 指南](07-database-schema-guide.md)
- [10 测试与质量指南](10-testing-quality-guide.md)
- `/Users/xjf/Public/Code/Agent-Project/docs/benchmark-results.md`
