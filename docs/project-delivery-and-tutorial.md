# Project Delivery Record and Complete Tutorial

[English](project-delivery-and-tutorial.md) | [简体中文](zh-CN/project-delivery-and-tutorial.md)

Date: `2026-03-24`

## 1. Purpose

This document answers two practical questions:

1. What has been built so far?
2. How should someone run, validate, demo, and extend the project?

It acts as a delivery record, a long-form repository guide, a demo script companion, and a high-level index for future work.

## 2. Project Goal

`agent-memory` is a zero-config, traceable, MCP-native long-term memory engine for agents.

- Installation: `pip install`
- Default storage: local `SQLite`
- Core capabilities:
  - long-term memory storage
  - intent-aware retrieval
  - causal tracing
  - conflict detection
  - adaptive forgetting
  - memory health monitoring
  - MCP tool integration

The project is positioned as an agent memory system rather than a generic vector database.

Naming:

- GitHub repository: `agent-memory`
- PyPI distribution: `agent-memory-engine`
- CLI command: `agent-memory`

## 3. What Has Been Completed

### 3.1 Core capabilities

**Storage**

- `SQLiteBackend` with schema bootstrap and WAL mode
- Core tables for memories, vectors, entities, relations, evolution logs, audit logs, and metadata
- FTS5 full-text search plus schema indexes for common filters and trace paths

**Retrieval**

- Semantic search with `sqlite-vec` support and a safe cosine-scan fallback
- Full-text search, entity lookup, and causal ancestor traversal
- Rule-based intent routing
- Reciprocal Rank Fusion for multi-strategy ranking

**Governance**

- Health reporting
- Conflict detection
- Forgetting policy
- Consolidation planning
- Audit and evolution inspection
- JSONL export and import

**Interfaces**

- Python SDK via `MemoryClient`
- CLI via `agent-memory`
- MCP server via `agent_memory.interfaces.mcp_server`
- REST adapter in `rest_api.py`

**Intelligence layer**

- Conversation-to-memory extraction pipeline
- LLM-first extraction with heuristic fallback
- Lightweight OpenAI and Ollama client adapters

### 3.2 Engineering work

**Project foundation**

- `.gitignore`
- `LICENSE`
- GitHub Actions CI in `.github/workflows/ci.yml`

**Testing**

- shared fixtures in `tests/conftest.py`
- deterministic dummy embeddings for stable test runs
- MCP regression coverage

**Examples**

- `examples/demo_cross_session.py`
- `examples/interactive_chat.py`
- `examples/mcp_server.py`

**Benchmarking**

- synthetic LOCOMO-Lite dataset expansion
- `benchmarks/locomo_lite/evaluate.py`
- generated benchmark artifact in `benchmarks/locomo_lite/latest_results.json`

**Documentation**

- polished `README.md`
- `CHANGELOG.md`
- benchmark, MCP, release, and delivery docs
- expansion review in `docs/plans/2026-03-24-agent-memory-expansion-review.md`

**Publishing**

- git initialization and GitHub publishing
- built artifacts:
  - `dist/agent_memory_engine-0.1.1-py3-none-any.whl`
  - `dist/agent_memory_engine-0.1.1.tar.gz`
- GitHub Releases
- PyPI publishing

### 3.3 Important fixes made during delivery

**SQLite thread safety for MCP**

- Symptom: MCP calls failed with SQLite thread-binding errors
- Fix: use `check_same_thread=False`

**Embedding JSON serialization**

- Symptom: `numpy.float32` embeddings could not be serialized cleanly
- Fix: normalize embedding values to native Python `float`

**Slow and unstable test startup**

- Symptom: tests could trigger local model downloads
- Fix: use dummy embedding providers in `tests/conftest.py`

**MCP import-time warnings**

- Symptom: importing interface modules could emit startup noise
- Fix: switch to lazy exports in `interfaces/__init__.py`

## 4. Current Completion Status

From a delivery perspective, the project is already complete enough to be run, demoed, tested, packaged, and published.

**Already complete**

- local run path
- storage and retrieval
- MCP integration
- benchmark workflow
- test suite
- packaging
- demo scripts

**Still worth deepening**

- temporal retrieval semantics
- consolidation quality
- extraction post-processing and deduplication
- full `OpenAIEmbeddingProvider` integration
- migrations, multi-tenancy, and observability

## 5. Repository Layout

```text
agent-memory/
├── .github/workflows/ci.yml
├── benchmarks/
│   ├── bench_retrieval.py
│   ├── bench_storage.py
│   └── locomo_lite/
├── docs/
│   ├── benchmark-results.md
│   ├── mcp-integration.md
│   ├── project-delivery-and-tutorial.md
│   ├── release-and-pypi.md
│   └── plans/
├── examples/
├── src/agent_memory/
└── tests/
```

## 6. How to Run the Project

Install from PyPI:

```bash
pip install agent-memory-engine
```

Run from source:

```bash
git clone https://github.com/bakebakebakebake/agent-memory.git
cd agent-memory
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Basic CLI validation:

```bash
agent-memory store "User prefers SQLite for local-first agents." --source-id demo
agent-memory search "What database does the user prefer?"
agent-memory health
```

## 7. How to Validate the Project

**Run tests**

```bash
.venv/bin/python -m pytest -q
```

**Build packages**

```bash
.venv/bin/python -m build
```

**Run benchmark**

```bash
.venv/bin/python benchmarks/locomo_lite/evaluate.py
cat benchmarks/locomo_lite/latest_results.json
```

**Run MCP server**

```bash
pip install -e .[mcp]
python -m agent_memory.interfaces.mcp_server
```

## 8. Suggested Demo Flow

For a short product demo:

1. store a preference memory
2. ask a factual recall question
3. ask a causal question
4. inspect the trace graph
5. inspect the health report

Recommended prompts:

- “Please remember that I prefer SQLite for local-first agent projects.”
- “What database do I prefer?”
- “Why did I choose SQLite?”
- “Show the trace for that memory.”
- “Show the current memory health report.”

## 9. Release Status

Current public release state:

- GitHub Release: `v0.1.0`
- GitHub Release: `v0.1.1`
- PyPI package: `agent-memory-engine==0.1.1`

Key references:

- `CHANGELOG.md`
- `docs/release-and-pypi.md`
- `docs/benchmark-results.md`

## 10. Recommended Next Steps

The project is already suitable for public presentation, but the clearest next improvements are:

- make `sqlite-vec` status observable in health reports
- improve structured conversation extraction and deduplication
- deepen temporal retrieval
- strengthen consolidation into topic-level summaries
- add migrations and multi-tenant isolation

For the longer roadmap, see `docs/plans/2026-03-24-agent-memory-expansion-review.md`.
