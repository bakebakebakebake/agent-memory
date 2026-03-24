# Project Delivery Record and Tutorial

[English](project-delivery-and-tutorial.md) | [简体中文](zh-CN/project-delivery-and-tutorial.md)

Date: `2026-03-25`

## 1. Purpose

This document answers two practical questions:

1. What is already implemented in the repository today?
2. How should someone run, validate, demo, and extend it?

## 2. Project Goal

`agent-memory` is a local-first, traceable, MCP-native long-term memory engine for agents.

It now spans two execution modes:

- embedded mode through the Python `MemoryClient`
- service mode through the Go server over REST and gRPC

## 3. What Has Been Completed

### 3.1 Core capabilities

**Python intelligence layer**

- `MemoryClient` as the unified SDK entrypoint
- embedding provider, entity extractor, conversation pipeline, conflict detector, trust scorer, forgetting policy, and governance helpers
- MCP server with 11 tools

**Go service layer**

- SQLite storage engine in `go-server/internal/storage/sqlite.go`
- 18 gRPC RPCs from `proto/memory/v1/storage_service.proto`
- 19 REST operations including `/health`, `/metrics`, and `/api/v1/info`
- auth hooks for API Key and JWT
- Prometheus metrics, `slog`, tracing bootstrap, and graceful shutdown
- lightweight Go CLI via Cobra

**Retrieval and governance**

- semantic, full-text, entity, and causal-trace retrieval
- rule-based intent router
- Reciprocal Rank Fusion
- contradiction edges, audit log, evolution log, JSONL export, and health snapshots

### 3.2 Engineering work

**Testing**

- existing Python test suite remains in place
- Go coverage now includes orchestrator, auth, config, governance, storage, forgetting, and trust tests
- Go benchmark coverage now includes storage, router, and orchestrator benchmarks

**Build and packaging**

- Docker Compose in `deploy/docker-compose.yml`
- multi-stage Go container in `deploy/Dockerfile.go-server`
- Python container in `deploy/Dockerfile.python-ai`
- CI now runs Python tests/build plus `go test ./...` and `go test -race ./...`

**Performance assets**

- `benchmarks/compare_go_python.py`
- `benchmarks/k6/http-load.js`
- `benchmarks/k6/grpc-load.js`

### 3.3 Important fixes and additions in this delivery round

- added `/api/v1/info` for version, build, runtime, and uptime inspection
- added dedicated Go tests for auth, config, governance, orchestrator, storage edge cases, forgetting, and trust
- added native Go benchmarks and Python-vs-Go comparison tooling
- rebuilt the documentation system around `docs/teaching/`

## 4. Current Completion Status

The repository is now suitable for:

- local SDK usage
- service deployment
- REST / gRPC demos
- MCP integration
- benchmark and comparison runs
- interview walkthroughs backed by dedicated teaching docs

Areas still worth deepening later:

- server-side vector acceleration beyond cosine scan
- multi-tenant isolation
- richer conflict adjudication
- scheduled governance jobs

## 5. Repository Layout

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

## 6. How to Run the Project

### Embedded mode

```bash
pip install agent-memory-engine
agent-memory store "User prefers SQLite for local-first agents." --source-id demo
agent-memory search "Why SQLite?"
```

### Service mode from source

```bash
git clone https://github.com/bakebakebakebake/agent-memory.git
cd agent-memory
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,remote]'
cd go-server && go run ./cmd/server
```

## 7. How to Validate the Project

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

## 8. Suggested Demo Flow

1. store one preference memory
2. ask a factual question
3. ask a causal question
4. open the trace graph
5. inspect `/health`
6. inspect `/api/v1/info`

Suggested prompts:

- “Please remember that I prefer SQLite for local-first agent projects.”
- “What database do I prefer?”
- “Why did I choose SQLite?”
- “Show the trace for that memory.”
- “Show the current memory health report.”

## 9. Key Documentation

- `docs/teaching/01-project-overview.md`
- `docs/teaching/02-architecture-deep-dive.md`
- `docs/teaching/03-algorithm-guide.md`
- `docs/teaching/11-performance-benchmarking.md`
- `docs/teaching/12-interview-guide.md`

## 10. Recommended Next Steps

- optimize Go vector-search hot path
- add multi-tenant isolation
- schedule governance tasks as recurring jobs
- deepen service-side operational tooling
