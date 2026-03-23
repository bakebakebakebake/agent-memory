# Agent Memory MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a usable Phase 1 `agent-memory` package with SQLite persistence, a Python SDK, basic extraction, and validated routing/forgetting primitives.

**Architecture:** Start with a local-only core centered on `MemoryClient` and `SQLiteBackend`. Keep interfaces protocol-first so storage, embeddings, and future LLM/MCP integrations can be swapped without rewriting business logic.

**Tech Stack:** Python 3.10+, SQLite/FTS5, pytest, sentence-transformers with deterministic fallback

---

### Task 1: Scaffold package and packaging

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/agent_memory/__init__.py`
- Create: `src/agent_memory/config.py`

**Step 1: Write the failing test**

Add an import smoke test for `MemoryClient`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py -v`
Expected: import failure because package does not exist yet.

**Step 3: Write minimal implementation**

Create packaging metadata and module exports for the package root.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_client.py -v`
Expected: import succeeds.

### Task 2: Build SQLite persistence core

**Files:**
- Create: `src/agent_memory/models.py`
- Create: `src/agent_memory/storage/base.py`
- Create: `src/agent_memory/storage/schema.sql`
- Create: `src/agent_memory/storage/sqlite_backend.py`
- Test: `tests/test_sqlite_backend.py`

**Step 1: Write the failing test**

Cover create/get/search/delete and causal ancestor tracing in an in-memory database.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sqlite_backend.py -v`
Expected: backend missing or methods unimplemented.

**Step 3: Write minimal implementation**

Implement schema bootstrap, CRUD, FTS5 search, semantic fallback search, entity index, audit/evolution logging, and recursive CTE tracing.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sqlite_backend.py -v`
Expected: all backend tests pass.

### Task 3: Add retrieval logic and SDK

**Files:**
- Create: `src/agent_memory/controller/router.py`
- Create: `src/agent_memory/controller/forgetting.py`
- Create: `src/agent_memory/embedding/base.py`
- Create: `src/agent_memory/embedding/local_provider.py`
- Create: `src/agent_memory/client.py`
- Test: `tests/test_router.py`
- Test: `tests/test_forgetting.py`
- Test: `tests/test_client.py`

**Step 1: Write the failing test**

Cover intent classification, RRF fusion, forgetting transitions, and end-to-end client add/search/delete.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_router.py tests/test_forgetting.py tests/test_client.py -v`
Expected: missing symbols or incorrect behavior.

**Step 3: Write minimal implementation**

Implement a rule-based router, Ebbinghaus-inspired decay helpers, embedding abstraction, deterministic fallback embeddings, and `MemoryClient`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_router.py tests/test_forgetting.py tests/test_client.py -v`
Expected: tests pass with no external services.

### Task 4: Add extraction pipeline and developer example

**Files:**
- Create: `src/agent_memory/extraction/entity_extractor.py`
- Create: `src/agent_memory/extraction/pipeline.py`
- Create: `examples/basic_usage.py`
- Test: `tests/test_extraction.py`

**Step 1: Write the failing test**

Cover simple conversation ingestion and entity extraction.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_extraction.py -v`
Expected: extraction modules missing.

**Step 3: Write minimal implementation**

Implement a heuristic extractor that can bootstrap memory creation from conversations before the LLM pipeline lands.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_extraction.py -v`
Expected: extracted drafts are stable and testable.

### Task 5: Validate the MVP

**Files:**
- Modify: `README.md`
- Test: `tests/test_client.py`
- Test: `tests/test_sqlite_backend.py`
- Test: `tests/test_router.py`
- Test: `tests/test_forgetting.py`
- Test: `tests/test_extraction.py`

**Step 1: Run targeted tests**

Run: `pytest tests/test_sqlite_backend.py tests/test_router.py tests/test_forgetting.py tests/test_extraction.py tests/test_client.py -v`

**Step 2: Run the full suite**

Run: `pytest`

**Step 3: Document gaps**

Record what remains for conflict detection, trust scoring, MCP tools, health monitoring, and REST API.

