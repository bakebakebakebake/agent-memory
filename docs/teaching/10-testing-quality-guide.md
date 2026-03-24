# 10 测试与质量指南
> 从测试分层、Go 补测、基准测试和 CI 四个角度，讲清项目如何保障质量。

## 前置知识

- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)

## 本文目标

完成阅读后，你将理解：

1. Python 与 Go 的测试分别覆盖哪些层次
2. 这次补充了哪些 Go 测试与基准
3. 如何本地运行测试、基准和对比脚本
4. CI 当前验证了哪些内容

## 测试架构总览

项目现在有两套测试面：

- **Python**：偏 SDK、后端、MCP 和集成行为
- **Go**：偏服务端、编排器、认证、治理和存储实现

## Python 测试基础设施

Python 侧关键基础设施包括：

- `tests/conftest.py`
- dummy embedding provider
- 内存数据库或临时 SQLite 文件

这样做的目的很明确：测试不要依赖真实模型下载。

## Go 测试基础设施

这次补充后的 Go 侧主要测试文件包括：

- `go-server/internal/search/orchestrator_test.go`
- `go-server/internal/auth/jwt_test.go`
- `go-server/internal/auth/apikey_test.go`
- `go-server/internal/config/config_test.go`
- `go-server/internal/governance/health_test.go`
- `go-server/internal/governance/export_test.go`
- `go-server/internal/storage/sqlite_test.go`
- `go-server/internal/controller/forgetting_test.go`
- `go-server/internal/controller/trust_test.go`

基准测试文件包括：

- `go-server/internal/storage/sqlite_bench_test.go`
- `go-server/internal/search/orchestrator_bench_test.go`
- `go-server/internal/controller/router_bench_test.go`

## 测试分类

### 单元测试

关注单个函数或规则模块，例如：

- 路由分类
- RRF
- forgetting policy
- trust scorer

### 集成测试

关注模块组合，例如：

- SQLite backend
- HTTP 路由
- gRPC service

### 回归测试

关注曾经出过问题或容易反复出问题的路径，例如：

- 认证
- 审计日志
- 关系存在性判断

### 基准测试

关注吞吐、延迟与分配情况，例如：

- `AddMemory`
- `SearchByVector`
- `BenchmarkOrchestratorSearch`

## 本地运行方式

### Go 测试

```bash
cd /Users/xjf/Public/Code/Agent-Project/go-server
go test ./...
```

### Go 基准

```bash
cd /Users/xjf/Public/Code/Agent-Project/go-server
go test -run=^$ -bench=. ./...
```

### Python 测试

```bash
cd /Users/xjf/Public/Code/Agent-Project
.venv/bin/python -m pytest -q
```

### Go / Python 对比

```bash
cd /Users/xjf/Public/Code/Agent-Project
PYTHONPATH=src .venv/bin/python benchmarks/compare_go_python.py
```

## CI 流水线

当前 `.github/workflows/ci.yml` 分成两个 job：

- `python`：Python 3.10 / 3.11 / 3.12 矩阵，执行 `pytest` 与 `python -m build`
- `go`：执行 `go test ./...` 和 `go test -race ./...`

这样分开后，职责更清晰，也避免在每个 Python 矩阵里重复跑 Go 测试。

## 质量目标

当前最值得关注的质量目标有：

- 检索策略行为稳定
- 认证行为稳定
- 治理日志与主数据一致
- 基准测试具备可复现的对比口径

## 如何新增一个 Go 测试

建议流程：

1. 先找同目录下已有测试风格
2. 选择 mock backend 或 `:memory:` SQLite
3. 只验证一个清晰行为
4. 若涉及边界条件，把阈值、空值和上限都补上

## 小结

- 项目当前已有 Python 与 Go 两套质量保障面
- 这次补充后，Go 端的测试覆盖明显更完整
- 基准、对比和 CI 已经形成一套闭环
- 若继续深化，建议下一步补充更细的端到端服务测试

## 延伸阅读

- [11 性能与基准测试](11-performance-benchmarking.md)
- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)
