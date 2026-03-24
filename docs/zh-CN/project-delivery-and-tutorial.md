# Agent Memory 项目交付记录与完整教程

[English](../project-delivery-and-tutorial.md) | [简体中文](project-delivery-and-tutorial.md)

日期：`2026-03-24`

## 1. 文档用途

这份文档回答两个核心问题：

1. 这个项目目前到底做到了什么程度？
2. 别人拿到仓库之后，应该如何运行、验证、演示与继续扩展？

它可以同时作为：

- 项目交付说明
- GitHub 仓库的长文档入口
- 对外介绍时的讲解脚本参考
- 后续迭代时的总索引

## 2. 项目目标

`agent-memory` 是一个零配置、可追溯、MCP 原生的 Agent 长期记忆引擎。

- 安装方式：`pip install`
- 默认存储：本地 `SQLite`
- 核心能力：
  - 长期记忆存储
  - 意图感知检索
  - 因果追溯
  - 冲突检测
  - 自适应遗忘
  - 记忆健康监控
  - MCP 工具集成

它的定位不是“另一个向量库”，而是一个面向 Agent 工作流的记忆系统。

命名：

- GitHub 仓库：`agent-memory`
- PyPI 包名：`agent-memory-engine`
- CLI 命令：`agent-memory`

## 3. 已完成内容

### 3.1 核心能力

**存储层**

- 基于 `SQLiteBackend`
- 包含 memories、vectors、entities、relations、evolution、audit、metadata 等表
- 支持 WAL
- 支持 FTS5 全文检索
- 支持常用查询与追溯路径索引

**检索层**

- 语义检索，优先 `sqlite-vec`
- 不可用时自动回退到 Python 余弦扫描
- 支持全文、实体和因果祖先检索
- 基于规则的意图路由
- 基于 RRF 的多路结果融合

**治理层**

- 健康报告
- 冲突检测
- 遗忘策略
- 巩固规划
- 审计和演化历史查看
- JSONL 导出导入

**接口层**

- Python SDK：`MemoryClient`
- CLI：`agent-memory`
- MCP Server：`agent_memory.interfaces.mcp_server`
- REST 适配层：`rest_api.py`

**智能层**

- 对话到记忆的提取管线
- LLM 优先、规则兜底
- OpenAI / Ollama 轻量客户端

### 3.2 工程化工作

**基础工程**

- `.gitignore`
- `LICENSE`
- GitHub Actions CI

**测试**

- `tests/conftest.py`
- 稳定的 dummy embeddings
- MCP 回归测试

**示例**

- `examples/demo_cross_session.py`
- `examples/interactive_chat.py`
- `examples/mcp_server.py`

**Benchmark**

- 扩展 LOCOMO-Lite 风格数据
- `benchmarks/locomo_lite/evaluate.py`
- `benchmarks/locomo_lite/latest_results.json`

**文档**

- `README.md`
- `CHANGELOG.md`
- benchmark、MCP、发布与交付文档
- 扩展优化建议文档

**发布**

- Git 初始化与 GitHub 推送
- wheel / sdist 打包
- GitHub Releases
- PyPI 发布

### 3.3 已修复的重要问题

**MCP 场景下的 SQLite 线程问题**

- 现象：MCP 调用时出现 SQLite thread error
- 修复：使用 `check_same_thread=False`

**embedding JSON 序列化问题**

- 现象：`numpy.float32` 无法直接 JSON 序列化
- 修复：统一转成原生 `float`

**测试触发模型下载**

- 现象：测试慢且不稳定
- 修复：默认使用 dummy embedding provider

**MCP 导入时告警**

- 现象：接口模块导入时出现噪音
- 修复：改为懒加载导出

## 4. 当前完成度

从项目交付角度看，当前版本已经可以：

- 本地运行
- 存储和检索
- 接入 MCP
- 跑 benchmark
- 运行测试
- 打包发布
- 做现场 demo

仍值得继续深化的方向：

- 时间语义检索
- 巩固质量
- 提取去重和后处理
- 完整的 `OpenAIEmbeddingProvider`
- migration、多租户和可观测性

## 5. 目录结构

```text
agent-memory/
├── .github/workflows/ci.yml
├── benchmarks/
├── docs/
├── examples/
├── src/agent_memory/
└── tests/
```

## 6. 如何运行项目

从 PyPI 安装：

```bash
pip install agent-memory-engine
```

从源码运行：

```bash
git clone https://github.com/bakebakebakebake/agent-memory.git
cd agent-memory
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

基本 CLI 验证：

```bash
agent-memory store "用户偏好 SQLite 做本地优先 Agent 项目。" --source-id demo
agent-memory search "用户偏好什么数据库？"
agent-memory health
```

## 7. 如何验证项目

运行测试：

```bash
.venv/bin/python -m pytest -q
```

构建产物：

```bash
.venv/bin/python -m build
```

运行 benchmark：

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```

启动 MCP：

```bash
pip install -e .[mcp]
python -m agent_memory.interfaces.mcp_server
```

## 8. 推荐 Demo 流程

建议按下面顺序演示：

1. 写入一条偏好记忆
2. 问一个 factual 问题
3. 问一个 causal 问题
4. 查看 trace graph
5. 查看 health report

推荐提示词：

- “请记住：我偏好 SQLite 做本地优先 Agent 项目。”
- “我偏好什么数据库？”
- “为什么我选择 SQLite？”
- “展示这条记忆的追溯链。”
- “展示当前记忆健康报告。”

## 9. 当前发布状态

- GitHub Release：`v0.1.0`
- GitHub Release：`v0.1.1`
- GitHub Release：`v0.2.0`
- PyPI 包：`agent-memory-engine==0.2.0`

参考：

- `CHANGELOG.md`
- `docs/release-and-pypi.md`
- `docs/benchmark-results.md`

## 10. 下一步建议

下一阶段最值得做的事情：

- 在 health 里暴露 `sqlite-vec` 状态
- 做更强的结构化提取和去重
- 补强 temporal retrieval
- 把 consolidation 深化成主题级压缩
- 增加 migration 与多租户隔离

更长的路线图见：

- `docs/zh-CN/plans/2026-03-24-agent-memory-expansion-review.md`
