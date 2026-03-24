# 08 部署指南
> 从嵌入模式、服务模式到 Docker Compose，整理项目的部署与运行方式。

## 前置知识

- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)

## 本文目标

完成阅读后，你将理解：

1. 如何部署嵌入模式
2. 如何用 Docker Compose 跑服务模式
3. 部署时需要关心哪些环境变量
4. 生产化使用时要注意哪些运维点

## 嵌入模式部署

最短路径：

```bash
pip install agent-memory-engine
```

然后直接调用：

```bash
agent-memory store "User prefers SQLite." --source-id demo
agent-memory search "What database does the user prefer?"
```

这条路径不依赖额外服务，最适合：

- 本地脚本
- 个人 Agent
- 单机工具

## 服务模式部署

仓库已经提供 **`deploy/docker-compose.yml`**。

结构如下：

- `go-server`：Go 服务
- `python-ai`：Python 接口容器
- `agent-memory-data`：SQLite 数据卷

## Dockerfile 走读

### Go 服务

文件：**`deploy/Dockerfile.go-server`**

特点：

- 多阶段构建
- 先在 `golang:1.25` 中编译
- 再把二进制复制到 `debian:bookworm-slim`

### Python 容器

文件：**`deploy/Dockerfile.python-ai`**

特点：

- 基于 `python:3.12-slim`
- 直接安装当前项目
- 默认启动 MCP 服务器

## 环境变量

最常用变量包括：

- `AGENT_MEMORY_DATABASE_PATH`
- `AGENT_MEMORY_HTTP_ADDRESS`
- `AGENT_MEMORY_GRPC_ADDRESS`
- `AGENT_MEMORY_MODE`
- `AGENT_MEMORY_GO_SERVER_URL`
- `AGENT_MEMORY_GRPC_TARGET`
- `AGENT_MEMORY_API_KEY`
- `AGENT_MEMORY_JWT_SECRET`
- `AGENT_MEMORY_REQUEST_TIMEOUT_SECONDS`

## 认证配置

若要开启认证，通常需要配置：

- `AGENT_MEMORY_API_KEY`
- `AGENT_MEMORY_JWT_SECRET`

HTTP 侧走 header，gRPC 侧走 metadata。

## 健康与监控

服务启动后，至少应检查：

- `/health`
- `/metrics`
- `/api/v1/info`

这三个入口分别回答：

- 当前健康状态如何
- 指标有没有正常上报
- 版本、构建信息和运行模式是什么

## 生产注意事项

### 数据文件与卷挂载

`SQLite` 的主文件、`-wal` 和 `-shm` 文件都需要被正确保留。容器部署时建议把数据库目录映射到持久卷。

### 备份

单文件数据库的优势是备份直接，但仍建议：

- 在低写入窗口备份
- 同时关注主文件和 `WAL`
- 保留演化与审计日志

### 扩展边界

当前方案适合：

- 单节点
- 本地优先
- 中小规模 Agent 负载

如果未来出现更高并发写入或多租户隔离需求，需要重新评估存储层。

## 推荐部署路径

### 本地开发

```bash
pip install -e '.[dev,remote]'
cd go-server && go run ./cmd/server
```

### Compose 启动

```bash
docker compose -f deploy/docker-compose.yml up --build
```

## 小结

- 嵌入模式部署最简单
- 服务模式更适合展示协议层和可观测性
- 仓库已经提供 Compose 与两个 Dockerfile
- 生产化重点是数据卷、认证、监控和单节点边界管理

## 延伸阅读

- [04 Go 服务端指南](04-go-server-guide.md)
- [09 API 参考](09-api-reference.md)
- [11 性能与基准测试](11-performance-benchmarking.md)
