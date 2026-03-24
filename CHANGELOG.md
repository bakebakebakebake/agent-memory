# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-03-25

### Added

- Added a Go service workspace with SQLite storage, schema migration, REST gateway, gRPC server, auth hooks, metrics bootstrap, tracing bootstrap, and Cobra CLI.
- Added shared Protobuf contracts plus generated Go and Python bindings under `proto/`, `go-server/gen/`, and `src/agent_memory/generated/`.
- Added a `RemoteBackend` so the Python SDK can talk to the Go service over HTTP or gRPC.
- Added Docker-based deployment assets for the Go server and Python AI layer.
- Added remote-backend integration tests, including a live Go gRPC smoke test.

### Changed

- Extended `MemoryClient` and configuration to support `embedded` and `remote` execution modes.
- Moved fused retrieval orchestration for service mode into the Go server so remote search runs on the storage side.
- Updated README, architecture docs, release docs, and top-level build tooling for the dual-language layout.

### Fixed

- Fixed gRPC relation-existence checks in the Python remote backend to read the generated boolean response correctly.

## [0.1.1] - 2026-03-24

### Fixed

- Fixed `sqlite-vec` index updates to avoid duplicate-key failures on memory update.
- Fixed CLI database lifecycle handling by closing the client after each command.
- Fixed embedding serialization by normalizing vector values to native Python `float`.
- Fixed cross-thread SQLite access for MCP-style workloads with `check_same_thread=False`.

### Changed

- Renamed the PyPI distribution to `agent-memory-engine`.
- Updated public-facing project metadata, README links, and release assets.
- Expanded delivery, MCP, benchmark, and expansion-review documentation.

## [0.1.0] - 2026-03-24

### Added

- Initial public release of `agent-memory`.
- SQLite backend with WAL, FTS5, entity index, audit log, evolution log, and causal links.
- `sqlite-vec` integration with safe fallback to Python cosine similarity search.
- Rule-based intent router with Reciprocal Rank Fusion.
- Adaptive forgetting, trust scoring, conflict detection, and consolidation planning.
- Python SDK, CLI, MCP server, REST adapter, examples, tests, and benchmark starter set.
