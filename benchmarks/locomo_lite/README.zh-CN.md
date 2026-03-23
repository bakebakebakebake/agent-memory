# LOCOMO-Lite

[English](README.md) | [简体中文](README.zh-CN.md)

这个目录包含 `agent-memory` 的一个合成评测起步数据集。

## 目的

- 对长期记忆检索做 sanity check
- 对比完整 intent-aware routing 与纯 semantic retrieval
- 为 README 和 release notes 提供可复现 benchmark

## 文件

- `sample_dialogues.jsonl` — 30 段多轮合成会话
- `sample_questions.jsonl` — 150 个带期望答案的 benchmark 问题
- `evaluate.py` — benchmark runner

## 评测流程

1. 将每段对话写入 `MemoryClient`
2. 用 `full` 模式跑所有问题
3. 再用 semantic-only baseline 重跑同一批问题
4. 计算各意图命中率与延迟统计

## 运行

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```
