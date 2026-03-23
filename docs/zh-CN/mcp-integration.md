# MCP 集成指南

[English](../mcp-integration.md) | [简体中文](mcp-integration.md)

本文说明如何将 `agent-memory` 作为 MCP Server 运行，并连接到支持 MCP 的客户端。

## Claude Desktop

1. 在与 `agent-memory` 相同的环境中安装 MCP 依赖：

```bash
pip install -e .[mcp]
```

2. 添加 MCP Server 配置：

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

3. 重启 Claude Desktop，确认 `agent-memory` 工具集已经出现。

## Codex / Cursor

将客户端指向同一个命令即可：

```bash
python -m agent_memory.interfaces.mcp_server
```

## 可用工具

- `memory_store(content, source_id, memory_type="semantic")`
- `memory_search(query, limit=5)`
- `memory_ingest_conversation(turns, source_id)`
- `memory_trace(memory_id, max_depth=10)`
- `memory_health()`
- `memory_audit(limit=50)`
- `memory_evolution(memory_id, limit=50)`
- `memory_update(memory_id, content)`
- `memory_delete(memory_id)`
- `memory_maintain()`
- `memory_export(path)`

## 示例交互

```text
User: Store that I prefer SQLite for local-first agent demos.
Client: Calls memory_store(...)

User: What database do I prefer?
Client: Calls memory_search("What database do I prefer?")

User: Show where that memory came from.
Client: Calls memory_trace("<memory-id>")
```

## 本地验证

```bash
pip install -e .[mcp]
python -m agent_memory.interfaces.mcp_server
```

如果没有安装 `fastmcp`，模块会打印安装提示而不是启动 stdio server。

可选的无客户端 smoke test：

```bash
python examples/mcp_server.py
```

## 故障排查

- 确认 `AGENT_MEMORY_DB_PATH` 指向可写路径
- 确认 `fastmcp` 安装在同一个 Python 环境中
- 如果客户端无法连接，先手动启动 server 检查 stdout/stderr
- 如果工具返回空结果，确认当前数据库文件中确实已有记忆
- 如果使用虚拟环境，确保客户端启动的是对应解释器
