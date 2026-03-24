# 09 API 参考
> 汇总 REST、gRPC、Python SDK、CLI 和 MCP 的主要接口，作为查阅手册使用。

## 前置知识

- 无

## 本文目标

完成阅读后，你将理解：

1. Go 服务当前暴露了哪些 REST 能力
2. gRPC `StorageService` 包含哪些 RPC
3. Python SDK、CLI 和 MCP 工具分别适合什么场景

## REST API

当前 HTTP 层可按“操作”理解为 19 个 REST 能力：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康快照 |
| `GET` | `/metrics` | Prometheus 指标 |
| `GET` | `/api/v1/info` | 版本、构建信息、运行时长 |
| `POST` | `/api/v1/memories` | 新增记忆 |
| `GET` | `/api/v1/memories` | 列表查询 |
| `GET` | `/api/v1/memories/{id}` | 查询单条记忆 |
| `PUT` | `/api/v1/memories/{id}` | 更新记忆 |
| `DELETE` | `/api/v1/memories/{id}` | 软删除记忆 |
| `POST` | `/api/v1/search/full-text` | 全文检索 |
| `POST` | `/api/v1/search/entities` | 实体检索 |
| `POST` | `/api/v1/search/vector` | 向量检索 |
| `POST` | `/api/v1/search/query` | 融合检索 |
| `POST` | `/api/v1/touch` | 刷新访问时间 |
| `GET` | `/api/v1/trace/ancestors` | 追祖先链 |
| `GET` | `/api/v1/trace/descendants` | 追后代链 |
| `GET` | `/api/v1/relations` | 列关系 |
| `POST` | `/api/v1/relations` | 建关系 |
| `GET` | `/api/v1/relations/exists` | 判定关系是否存在 |
| `GET` | `/api/v1/evolution` | 读取演化事件 |
| `GET` | `/api/v1/audit` | 读取审计事件 |

### 示例：新增记忆

```bash
curl -X POST http://127.0.0.1:8080/api/v1/memories \
  -H 'Content-Type: application/json' \
  -d '{
    "id":"demo-1",
    "content":"SQLite works well for local-first agents.",
    "memory_type":"semantic",
    "embedding":[0.1,0.2,0.3],
    "created_at":"2026-03-25T00:00:00Z",
    "last_accessed":"2026-03-25T00:00:00Z",
    "trust_score":0.8,
    "importance":0.6,
    "layer":"short_term",
    "decay_rate":0.1,
    "source_id":"demo",
    "entity_refs":["sqlite","agent"],
    "tags":["demo"]
  }'
```

### 示例：融合检索

```bash
curl -X POST http://127.0.0.1:8080/api/v1/search/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"为什么选择 SQLite","embedding":[0.1,0.2,0.3],"entities":["sqlite"],"limit":5}'
```

## gRPC API

`StorageService` 当前提供 18 个 RPC：

- `AddMemory`
- `GetMemory`
- `UpdateMemory`
- `DeleteMemory`
- `SearchQuery`
- `SearchFullText`
- `SearchByEntities`
- `SearchByVector`
- `TouchMemory`
- `TraceAncestors`
- `TraceDescendants`
- `ListMemories`
- `AddRelation`
- `ListRelations`
- `RelationExists`
- `GetEvolutionEvents`
- `GetAuditEvents`
- `HealthCheck`

### 示例：Python gRPC 调用

```python
response = stub.SearchQuery(
    storage_service_pb2.SearchQueryRequest(
        query="为什么选择 SQLite",
        embedding=[0.1, 0.2, 0.3],
        entities=["sqlite"],
        limit=5,
    )
)
```

## Python SDK

面向调用方的主要公开方法：

- `add()`
- `get()`
- `update()`
- `delete()`
- `search()`
- `trace()`
- `trace_graph()`
- `ingest_conversation()`
- `maintain()`
- `health()`
- `audit_events()`
- `evolution_events()`
- `export_jsonl()`
- `import_jsonl()`

### 示例：SDK 调用

```python
from agent_memory import MemoryClient

client = MemoryClient()
item = client.add("User prefers SQLite.", source_id="demo")
results = client.search("What database does the user prefer?")
```

## CLI 命令

### Python CLI：`agent-memory`

- `store`
- `search`
- `trace`
- `evolution`
- `audit`
- `health`
- `maintain`
- `export`
- `import`

### Go CLI：`agent-memory-go`

- `health`
- `store`
- `search`

## MCP 工具

当前 MCP 层暴露 11 个工具：

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

## 小结

- REST 适合调试和通用脚本
- gRPC 适合强类型远程调用
- Python SDK 负责统一开发体验
- CLI 和 MCP 让仓库能接更多实际入口

## 延伸阅读

- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)
- [06 Protobuf 与 gRPC 通信](06-protobuf-grpc-guide.md)
