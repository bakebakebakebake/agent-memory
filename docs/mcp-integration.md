# MCP Integration

This document describes how to run `agent-memory` as an MCP server and connect it to supported MCP clients.

## Claude Desktop

1. Install MCP dependencies in the same environment as `agent-memory`:

```bash
pip install -e .[mcp]
```

2. Add an MCP server entry:

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

3. Restart Claude Desktop and verify the `agent-memory` toolset appears.

## Cursor

Point Cursor to the same command:

```bash
python -m agent_memory.interfaces.mcp_server
```

## Available Tools

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

## Example Interaction

```text
User: Store that I prefer SQLite for local-first agent demos.
Claude: Calls memory_store(...)

User: What database do I prefer?
Claude: Calls memory_search("What database do I prefer?")

User: Show where that memory came from.
Claude: Calls memory_trace("<memory-id>")
```

## Local Verification

```bash
pip install -e .[mcp]
python -m agent_memory.interfaces.mcp_server
```

If `fastmcp` is not installed, the module prints an install hint instead of starting the stdio server.

Optional smoke check without Claude Desktop:

```bash
python examples/mcp_server.py
```

## Troubleshooting

- Verify `AGENT_MEMORY_DB_PATH` points to a writable file path
- Ensure `fastmcp` is installed in the same Python environment
- If the client cannot connect, run the server manually and inspect stderr/stdout
- If tools return empty results, check whether the chosen DB file already contains memories
- If you use a virtual environment, make sure Claude/Cursor launches that exact interpreter

## Screenshots

Place validated screenshots in `docs/screenshots/` after local client verification.
This repository currently reserves the directory but does not ship fabricated screenshots.
