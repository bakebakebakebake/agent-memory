# Changelog

All notable changes to this project are documented in this file.

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
