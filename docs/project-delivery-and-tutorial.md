# Agent Memory 项目交付记录与完整教程

日期：`2026-03-24`

## 1. 文档用途

这份文档回答两个问题：

1. **这个项目我们到底做了哪些事情**
2. **别人拿到项目后，应该如何完整使用、验证、演示、扩展**

它适合作为：

- 项目交付说明
- GitHub 仓库的深度文档
- 面试时的项目讲稿底稿
- 后续继续开发时的项目总索引

---

## 2. 项目目标

我们构建的是一个 **零配置、可追溯、MCP 原生的 Agent 长期记忆引擎**：

- 安装方式：`pip install`
- 默认存储：纯本地 `SQLite`
- 核心能力：
  - 长期记忆存储
  - 意图感知检索
  - 因果追溯
  - 冲突检测
  - 自适应遗忘
  - 记忆健康监控
  - MCP 工具化接入

这个项目的定位不是“又一个向量库”，而是一个 **面向 Agent 的 Memory System**。

补充说明：

- GitHub / 项目名：`agent-memory`
- PyPI 发布名：`agent-memory-engine`
- CLI 命令：`agent-memory`

---

## 3. 我们完成了哪些任务

## 3.1 核心能力实现

我们已经完成了以下核心模块：

### 存储层

- 实现了 `SQLiteBackend`
- 初始化了完整 `schema.sql`
- 支持：
  - `memories`
  - `memory_vectors`
  - `entity_index`
  - `relations`
  - `evolution_log`
  - `audit_log`
  - `memories_fts`
  - `backend_meta`
- 开启 `WAL`
- 增加了多类索引，覆盖：
  - `memory_type`
  - `layer`
  - `created_at`
  - `last_accessed`
  - `trust_score`
  - `source_id`
  - `causal_parent_id`
  - `supersedes_id`
  - `relations`
  - `audit/evolution`

### 检索层

- 实现了向量检索
- 优先走 `sqlite-vec`
- 不可用时自动回退为 Python 余弦扫描
- 实现了：
  - `semantic`
  - `full_text`
  - `entity`
  - `causal_trace`
- 通过 `IntentRouter` 做规则路由
- 通过 `Reciprocal Rank Fusion` 做结果融合

### 治理层

- 实现了记忆健康监控
- 实现了冲突检测
- 实现了遗忘策略
- 实现了记忆巩固基础能力
- 实现了审计日志读取
- 实现了 JSONL 导出导入

### 接口层

- Python SDK：`MemoryClient`
- CLI：`agent-memory`
- MCP Server：`agent_memory.interfaces.mcp_server`
- REST fallback：`rest_api.py`

### 智能层

- 实现了对话记忆提取管线
- 支持：
  - LLM 提取
  - heuristic fallback
- 实现了 OpenAI / Ollama LLM client 的轻量封装

---

## 3.2 我们新增/完善的工程化内容

除了核心功能，我们还补齐了大量“项目交付级”内容：

### 基础工程文件

- 新增 `.gitignore`
- 新增 `LICENSE`（MIT）
- 新增 GitHub Actions CI：
  - `.github/workflows/ci.yml`

### 测试基础设施

- 新增共享 fixture：`tests/conftest.py`
- 统一了测试 client 构建方式
- 增加了 MCP 回归测试
- 让测试默认使用离线 Dummy embedding，避免测试时下载模型

### Demo 与示例

- 新增跨会话 demo：
  - `examples/demo_cross_session.py`
- 新增交互式聊天 demo：
  - `examples/interactive_chat.py`
- 完善 MCP 启动脚本：
  - `examples/mcp_server.py`

### Benchmark

- 扩充 `LOCOMO-Lite` 样例数据
- 新增：
  - `30` 段 dialogues
  - `150` 个问题
- 实现 benchmark runner：
  - `benchmarks/locomo_lite/evaluate.py`
- 生成结构化结果：
  - `benchmarks/locomo_lite/latest_results.json`

### 文档

- 完善 `README.md`
- 新增 benchmark 文档：
  - `docs/benchmark-results.md`
- 新增 MCP 集成文档：
  - `docs/mcp-integration.md`
- 新增扩展优化建议文档：
  - `docs/plans/2026-03-24-agent-memory-expansion-review.md`

### 发布验证

- 完成 `git init`
- 生成打包产物：
  - `dist/agent_memory_engine-0.1.0-py3-none-any.whl`
  - `dist/agent_memory_engine-0.1.0.tar.gz`

---

## 3.3 我们修复过的重要问题

在交付过程中，我们还修掉了几个真实集成问题：

### 问题 1：MCP 调用时 SQLite 跨线程报错

**现象**

- FastMCP 调用 `memory_health` 时抛出：
  - `SQLite objects created in a thread can only be used in that same thread`

**修复**

- 将 SQLite 连接改为：
  - `check_same_thread=False`

### 问题 2：真实 embedding 返回 `numpy.float32`，无法 JSON 序列化

**现象**

- 在 `memory_store` / REST 创建记忆时，`json.dumps(item.embedding)` 报错

**修复**

- 新增 embedding 归一化逻辑
- 在写入 `memory_vectors` 和 `sqlite-vec` 序列化前统一转为原生 `float`

### 问题 3：测试会触发本地模型下载，慢且不稳定

**修复**

- `tests/conftest.py` 中默认改为 Dummy embedding provider

### 问题 4：MCP 模块导入时出现启动告警

**修复**

- 将 `interfaces/__init__.py` 改成懒加载导出

---

## 4. 目前项目的实际完成度

从交付角度看，目前项目已经完成到：

### 已完成

- 可本地运行
- 可存储和检索
- 可 MCP 调用
- 可 benchmark
- 可测试
- 可打包
- 可 demo

### 还未完全做深

- 时间语义检索仍有提升空间
- 巩固逻辑目前还是基础版本
- 提取后处理和重复抑制可以继续加强
- `OpenAIEmbeddingProvider` 还未完整接通
- 真正的迁移系统、多租户、观测能力仍可继续扩展

这也是为什么我们额外写了一份扩展建议文档。

---

## 5. 项目目录说明

```text
agent-memory/
├── .github/workflows/ci.yml
├── benchmarks/
│   ├── bench_retrieval.py
│   ├── bench_storage.py
│   └── locomo_lite/
├── docs/
│   ├── benchmark-results.md
│   ├── mcp-integration.md
│   ├── project-delivery-and-tutorial.md
│   └── plans/
├── examples/
├── src/agent_memory/
│   ├── client.py
│   ├── cli.py
│   ├── config.py
│   ├── controller/
│   ├── embedding/
│   ├── extraction/
│   ├── governance/
│   ├── interfaces/
│   ├── llm/
│   ├── models.py
│   └── storage/
└── tests/
```

---

## 6. 如何从零开始运行这个项目

## 6.1 创建虚拟环境

```bash
cd /Users/xjf/Public/Code/Agent-Project
python3 -m venv .venv
source .venv/bin/activate
```

## 6.2 安装基础依赖

```bash
pip install -e '.[dev]'
```

如果要使用 MCP：

```bash
pip install -e '.[mcp]'
```

如果要使用 REST API：

```bash
pip install -e '.[api]'
```

---

## 7. 如何运行测试

```bash
.venv/bin/python -m pytest -q
```

当前验证结果：

- `35 passed`

如果只跑 MCP 相关测试：

```bash
.venv/bin/python -m pytest -q tests/test_mcp_server.py
```

---

## 8. 如何使用 Python SDK

最小示例：

```python
from agent_memory import MemoryClient

client = MemoryClient()

item = client.add(
    "The user prefers SQLite for local-first agent projects.",
    source_id="demo-session",
)

results = client.search("What database does the user prefer?")
print(results[0].item.content)

trace = client.trace_graph(item.id)
print(trace.focus.content)

health = client.health()
print(health.suggestions)
```

常用能力：

- `client.add(...)`
- `client.get(memory_id)`
- `client.search(query)`
- `client.trace_graph(memory_id)`
- `client.delete(memory_id)`
- `client.health()`
- `client.audit_events()`
- `client.evolution_events()`
- `client.export_jsonl(path)`
- `client.import_jsonl(path)`
- `client.maintain()`

---

## 9. 如何使用 CLI

查看帮助：

```bash
PYTHONPATH=src .venv/bin/python -m agent_memory.cli --help
```

示例：

```bash
agent-memory store "User prefers SQLite." --source-id demo
agent-memory search "Why SQLite?"
agent-memory health
agent-memory trace <memory-id>
agent-memory export /tmp/memories.jsonl
```

---

## 10. 如何运行 Demo

## 10.1 跨会话演示

```bash
.venv/bin/python examples/demo_cross_session.py --db /tmp/agent-memory-demo.db
```

它会演示：

- 存储记忆
- 意图检索
- 冲突写入
- 因果追溯
- 维护任务
- 健康报告
- 导出导入
- 跨 session 持久化

## 10.2 交互式聊天演示

```bash
.venv/bin/python examples/interactive_chat.py --db chat_memory.db --provider none
```

可选 provider：

- `none`
- `openai`
- `ollama`

---

## 11. 如何使用 MCP

## 11.1 启动 MCP Server

```bash
PYTHONPATH=src .venv/bin/python -m agent_memory.interfaces.mcp_server
```

## 11.2 Claude Desktop 配置

配置示例：

```json
{
  "mcpServers": {
    "agent-memory": {
      "command": "python",
      "args": ["-m", "agent_memory.interfaces.mcp_server"],
      "env": {
        "AGENT_MEMORY_DB_PATH": "/absolute/path/to/default.db"
      }
    }
  }
}
```

## 11.3 MCP 可用工具

- `memory_store`
- `memory_search`
- `memory_ingest_conversation`
- `memory_trace`
- `memory_health`
- `memory_audit`
- `memory_evolution`
- `memory_update`
- `memory_delete`
- `memory_maintain`
- `memory_export`

## 11.4 我们已经做过的 MCP 验证

我们已经完成：

- FastMCP 启动验证
- `memory_health` 协议调用验证
- `memory_store` 协议调用验证
- `memory_search` 协议调用验证
- `memory_trace` 协议调用验证

也就是说，MCP 不是“写了代码但没验”，而是已经做过真实工具调用。

更多说明见：

- `docs/mcp-integration.md`

---

## 12. 如何运行 Benchmark

运行评测：

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
```

查看产物：

```bash
cat benchmarks/locomo_lite/latest_results.json
```

当前结果摘要：

- Overall hit rate：`50.0%`
- Semantic-only baseline：`23.3%`
- 提升：`+26.7pp`
- p95 latency：`16.64ms`

更多见：

- `docs/benchmark-results.md`

---

## 13. 如何构建发布产物

安装构建工具后：

```bash
.venv/bin/pip install build
.venv/bin/python -m build
```

生成产物：

- `dist/agent_memory_engine-0.1.0-py3-none-any.whl`
- `dist/agent_memory_engine-0.1.0.tar.gz`

---

## 14. 如何做版本管理

我们已经执行过：

```bash
git init
```

当前仓库已经是 Git 仓库。

你后续可以继续：

```bash
git branch -m main
git add .
git commit -m "feat: initial release of agent-memory"
```

---

## 15. 推荐阅读顺序

如果你是第一次看这个项目，建议按这个顺序：

1. `README.md`
2. `src/agent_memory/client.py`
3. `src/agent_memory/storage/sqlite_backend.py`
4. `src/agent_memory/controller/router.py`
5. `src/agent_memory/controller/forgetting.py`
6. `src/agent_memory/controller/conflict.py`
7. `src/agent_memory/interfaces/mcp_server.py`
8. `examples/demo_cross_session.py`
9. `docs/benchmark-results.md`
10. `docs/plans/2026-03-24-agent-memory-expansion-review.md`

---

## 16. 面试时可以怎么讲

你可以按下面结构讲：

### 一句话介绍

> 我做了一个零配置、本地优先、可追溯、MCP 原生的 Agent 长期记忆引擎。

### 技术亮点

- SQLite + WAL + FTS5 + sqlite-vec
- 意图感知路由 + RRF
- 因果追溯 + 冲突检测 + 遗忘策略
- MCP 工具化接入真实客户端
- 有 benchmark、有 demo、有测试、有打包产物

### 差异化

- 不依赖 Docker/Neo4j/Qdrant
- 强调本地可用性
- 强调记忆治理和可追溯
- 强调 Agent 接入而不是单纯 RAG

---

## 17. 下一步建议

如果继续做下去，优先建议看：

- `docs/plans/2026-03-24-agent-memory-expansion-review.md`

尤其推荐优先推进：

1. temporal 真过滤
2. extraction postprocessor
3. backend status / observability
4. conflict queue
5. topic-level consolidation

---

## 18. 文档索引

- 总览：`README.md`
- 本文档：`docs/project-delivery-and-tutorial.md`
- MCP 集成：`docs/mcp-integration.md`
- Benchmark：`docs/benchmark-results.md`
- 扩展规划：`docs/plans/2026-03-24-agent-memory-expansion-review.md`

这几份文档一起，已经构成这个项目当前阶段的完整文档体系。
