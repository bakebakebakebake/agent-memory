# Agent Memory Engine Architecture

This repository now supports two execution modes:

- Embedded mode: Python `MemoryClient` talks to `SQLiteBackend` directly.
- Service mode: Python `MemoryClient` talks to the Go storage service over REST or gRPC through `RemoteBackend`.

The Go service owns SQLite storage, schema migration, REST, gRPC, fused retrieval orchestration, auth hooks, metrics, tracing bootstrap, and a Cobra CLI.
The Python service keeps embeddings, extraction, MCP, and SDK ergonomics.
