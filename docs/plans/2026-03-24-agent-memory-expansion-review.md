# Agent Memory Expansion and Optimization Review

[English](2026-03-24-agent-memory-expansion-review.md) | [简体中文](../zh-CN/plans/2026-03-24-agent-memory-expansion-review.md)

Date: `2026-03-24`

## 1. Executive Summary

`agent-memory` is already a complete public prototype:

- SDK, SQLite storage, FTS, `sqlite-vec` integration, and fallback paths are present
- routing, forgetting, conflict handling, consolidation, health checks, and export/import all have working baseline implementations
- MCP, REST, CLI, demos, benchmarks, CI, and packaging are in place
- MCP tools have been validated in real FastMCP-style usage

At this stage, the main question is no longer “does the project have the pieces?” but “which capabilities should be deepened next to turn it into a standout long-term open-source system?”

Recommended priority order:

1. retrieval quality and performance
2. extraction / conflict / consolidation intelligence loop
3. production-grade engineering concerns
4. stronger evaluation and release quality

## 2. Current State

### 2.1 What is already strong

- zero-config local operation on SQLite + WAL
- correct high-level vector retrieval architecture
- interpretable rule routing plus RRF
- the right governance direction: health, audit, evolution, soft delete, causal chain
- a complete interface surface: SDK, CLI, MCP, REST
- broad technical depth across storage, retrieval, lifecycle, protocol integration, and evaluation

### 2.2 Current boundaries

- several “intelligence modules” are still baseline implementations
- some production-grade concerns are not yet systematized
- evaluation quality is enough for demos, but not yet strong enough for a research-like claim

## 3. Priority Recommendations

## P0: Highest priority

### P0-1. Make the vector retrieval path clearly production-ready

**Current state**

- `src/agent_memory/storage/sqlite_backend.py` supports `sqlite-vec`
- the fallback path still scans every vector
- the system does not yet expose whether a deployment is actually using `sqlite-vec`

**Why this matters**

- users and reviewers will ask how the system behaves at `10k+` or `100k+` memories
- observability is needed to prove the fast path is active

**Recommended work**

- expose:
  - `sqlite_vec_enabled`
  - `vector_index_dimension`
  - `vector_search_mode` (`sqlite_vec` / `fallback_scan`)
- add benchmarks at `1k / 10k / 100k`
- show fallback warnings or metadata when the Python scan path is active

### P0-2. Strengthen extraction with pre-noise filtering and post-extraction dedupe

**Current state**

- `src/agent_memory/extraction/pipeline.py` already supports LLM extraction plus heuristic fallback
- it does not yet include robust write-time dedupe or conflict prechecks

**Recommended work**

- add a `draft_postprocessor`
- dedupe drafts within a batch
- compare drafts against existing memories
- drop low-information drafts
- enrich drafts with:
  - `confidence`
  - `evidence_turns`
  - `extraction_method`

### P0-3. Upgrade temporal retrieval from recency sorting to time-constrained retrieval

**Current state**

- temporal routing mostly sorts by recency
- `valid_from` and `valid_until` are not fully leveraged during search

**Recommended work**

- add lightweight bilingual time parsing for phrases like “last week”, “recently”, and “before”
- support search-time filters for:
  - `created_at`
  - `valid_from`
  - `valid_until`
- return a `time_match_reason` for better interpretability

## P1: Best next-stage investments

### P1-1. Turn conflict handling into a staged governance workflow

Recommended additions:

- conflict states:
  - `pending`
  - `resolved_keep_both`
  - `resolved_supersede`
  - `needs_review`
- conflict queue
- background maintenance-based adjudication
- MCP and REST visibility into pending conflicts

### P1-2. Evolve consolidation from duplicate merging into topic compression

Recommended additions:

- split consolidation into:
  - `dedup_merge`
  - `topic_summary`
- persist:
  - `supersedes_id` chains
  - `derived_from` multi-edge relations
  - `consolidation_batch_id`

### P1-3. Add multi-tenant or multi-agent isolation

Recommended additions:

- `namespace` or `agent_id + user_id`
- tenant-aware filters for search and maintenance
- namespace support in MCP tools

## P2: Engineering and release quality

### P2-1. Add schema migrations

- add `schema_version`
- introduce migration files such as:
  - `storage/migrations/001_init.sql`
  - `storage/migrations/002_add_namespace.sql`
- auto-apply pending migrations on startup

### P2-2. Harden provider clients

- complete `OpenAIEmbeddingProvider`
- add:
  - timeouts
  - retries
  - exponential backoff
  - status-aware error classification
  - provider metrics

### P2-3. Improve observability

Recommended additions to health or telemetry output:

- `sqlite_vec_enabled`
- `embedding_provider`
- `avg_search_latency_ms`
- `conflict_queue_size`
- `consolidation_candidates`
- optional debug logging

## 4. Recommended Roadmap Narrative

The strongest next public narrative for the project is:

- **today**: a zero-config local-first memory engine with explainable retrieval and governance
- **next**: stronger retrieval quality, observable vector performance, and better structured extraction
- **later**: migrations, multi-tenant support, and production observability

That roadmap keeps the current public positioning honest while still making the next steps ambitious and concrete.
