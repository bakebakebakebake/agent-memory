# Agent Memory 项目交付记录与教程

[English](../project-delivery-and-tutorial.md) | [简体中文](project-delivery-and-tutorial.md)

日期：`2026-03-25`

## 1. 文档用途

这份文档回答两个问题：

1. 仓库现在已经做到了什么程度
2. 别人拿到仓库后该如何运行、验证、演示和继续扩展

## 2. 项目目标

`agent-memory` 是一个本地优先、可追溯、MCP 原生的 Agent 长期记忆引擎。

当前已经形成两种执行模式：

- Python `MemoryClient` 直接访问嵌入式后端
- Python 端通过 Go 服务访问远程后端

## 3. 已完成内容

### 3.1 核心能力

**Python 智能面**

- 统一入口 `MemoryClient`
- embedding、实体提取、对话提取、冲突检测、信任评分、遗忘与治理模块
- 11 个 MCP 工具

**Go 服务层**

- `go-server/internal/storage/sqlite.go` 中的 SQLite 存储引擎
- `proto/memory/v1/storage_service.proto` 中的 18 个 gRPC RPC
- 19 个 REST 操作，包含 `/health`、`/metrics` 和 `/api/v1/info`
- API Key / JWT 认证
- Prometheus 指标、`slog`、tracing 初始化与优雅关停
- Go CLI

**检索与治理**

- semantic / full-text / entity / causal trace
- 意图路由与 RRF
- contradiction 关系、审计日志、演化日志、JSONL 导出和健康快照

### 3.2 工程化工作

**测试**

- 保留既有 Python 测试体系
- 新增 Go 侧 orchestrator、auth、config、governance、storage、forgetting、trust 测试
- 新增 Go benchmark：storage、router、orchestrator

**构建与交付**

- `deploy/docker-compose.yml`
- `deploy/Dockerfile.go-server`
- `deploy/Dockerfile.python-ai`
- CI 现在同时运行 Python 测试/构建，以及 `go test ./...` 和 `go test -race ./...`

**性能资产**

- `benchmarks/compare_go_python.py`
- `benchmarks/k6/http-load.js`
- `benchmarks/k6/grpc-load.js`

### 3.3 本轮交付新增点

- 新增 `/api/v1/info`，方便读取版本、构建信息、运行时和 uptime
- 新增一批 Go 测试与边界覆盖
- 新增 Go 原生 benchmark、Go/Python 对比脚本与 k6 压测脚本
- 重建文档体系，入口放在 `docs/teaching/`

## 4. 当前完成度

当前仓库已经适合用于：

- 本地 SDK 使用
- 服务模式部署
- REST / gRPC 演示
- MCP 接入
- 基准与对比测试
- 面试项目讲解

后续仍值得继续做的方向：

- Go 向量检索继续提速
- 多租户隔离
- 更强的冲突复判
- 定时治理任务

## 5. 仓库结构

```text
agent-memory/
├── benchmarks/
│   ├── compare_go_python.py
│   ├── k6/
│   └── locomo_lite/
├── deploy/
├── docs/
│   ├── teaching/
│   └── zh-CN/
├── go-server/
├── proto/
├── src/agent_memory/
└── tests/
```

## 6. 如何运行项目

### 嵌入模式

```bash
pip install agent-memory-engine
agent-memory store "User prefers SQLite for local-first agents." --source-id demo
agent-memory search "Why SQLite?"
```

### 服务模式

```bash
git clone https://github.com/bakebakebakebake/agent-memory.git
cd agent-memory
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,remote]'
cd go-server && go run ./cmd/server
```

## 7. 如何验证项目

```bash
cd go-server && go test ./...
```

```bash
cd go-server && go test -run=^$ -bench=. ./...
```

```bash
.venv/bin/python -m pytest -q
```

```bash
PYTHONPATH=src .venv/bin/python benchmarks/compare_go_python.py --scales 100 1000
```

## 8. 推荐演示流程

1. 写入一条偏好记忆
2. 问一个 factual 问题
3. 问一个 causal 问题
4. 打开 trace graph
5. 查看 `/health`
6. 查看 `/api/v1/info`

推荐提示词：

- “请记住：我偏好 SQLite 做本地优先 Agent 项目。”
- “我偏好什么数据库？”
- “为什么我选择 SQLite？”
- “展示这条记忆的追踪链。”
- “展示当前健康报告。”

## 9. 关键文档

- `../teaching/01-project-overview.md`
- `../teaching/02-architecture-deep-dive.md`
- `../teaching/03-algorithm-guide.md`
- `../teaching/11-performance-benchmarking.md`
- `../teaching/12-interview-guide.md`

## 10. 下一步建议

- 优化 Go 向量检索热路径
- 增加多租户隔离
- 把治理任务做成可调度作业
- 继续补服务端运维工具链
