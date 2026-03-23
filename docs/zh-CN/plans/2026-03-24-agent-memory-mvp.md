# Agent Memory MVP 实施计划

[English](../../plans/2026-03-24-agent-memory-mvp.md) | [简体中文](2026-03-24-agent-memory-mvp.md)

## 目标

构建一个可用的 Phase 1 `agent-memory` 包，包含 SQLite 持久化、Python SDK、基础提取能力，以及经过验证的路由/遗忘原语。

## 架构原则

- 以本地优先的 `MemoryClient` + `SQLiteBackend` 为核心
- 使用协议与接口，便于未来替换存储、embedding 和 LLM 实现
- 优先可测试、可演示、可迭代

## 技术栈

- Python 3.10+
- SQLite / FTS5
- pytest
- sentence-transformers + deterministic fallback

## 任务拆分

### 任务 1：脚手架与打包

涉及文件：

- `pyproject.toml`
- `README.md`
- `src/agent_memory/__init__.py`
- `src/agent_memory/config.py`

步骤：

1. 先写 `MemoryClient` import smoke test
2. 运行测试，确认失败
3. 写最小可用实现
4. 再跑测试，确认通过

### 任务 2：SQLite 持久化核心

涉及文件：

- `src/agent_memory/models.py`
- `src/agent_memory/storage/base.py`
- `src/agent_memory/storage/schema.sql`
- `src/agent_memory/storage/sqlite_backend.py`
- `tests/test_sqlite_backend.py`

步骤：

1. 先写失败测试
2. 验证 backend 缺失或未实现
3. 实现 schema bootstrap、CRUD、FTS5、semantic fallback、entity index、audit/evolution、CTE trace
4. 再跑测试，确认通过

### 任务 3：检索逻辑与 SDK

涉及文件：

- `src/agent_memory/controller/router.py`
- `src/agent_memory/controller/forgetting.py`
- `src/agent_memory/embedding/base.py`
- `src/agent_memory/embedding/local_provider.py`
- `src/agent_memory/client.py`
- `tests/test_router.py`
- `tests/test_forgetting.py`
- `tests/test_client.py`

步骤：

1. 覆盖意图分类、RRF、遗忘层切换与端到端 add/search/delete
2. 补最小实现
3. 跑测试验证

### 任务 4：提取与接口

涉及文件：

- `src/agent_memory/extraction/*`
- `src/agent_memory/interfaces/*`
- `tests/test_extraction.py`
- `tests/test_mcp_server.py`

步骤：

1. 先补对话提取与 MCP 测试
2. 实现提取、MCP server 和必要的 fallback
3. 跑测试

### 任务 5：文档与验收

涉及文件：

- `README.md`
- `examples/`
- `benchmarks/`

步骤：

1. 提供 quickstart
2. 提供最小示例
3. 跑 smoke benchmark
4. 确认项目可展示
