from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
from math import sqrt
from pathlib import Path
import re
import sqlite3
from typing import Any

from agent_memory.models import MemoryItem, MemoryLayer, MemoryType, RelationEdge, RelationType


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    left_trimmed = left[:size]
    right_trimmed = right[:size]
    numerator = sum(a * b for a, b in zip(left_trimmed, right_trimmed, strict=False))
    left_norm = sqrt(sum(a * a for a in left_trimmed))
    right_norm = sqrt(sum(b * b for b in right_trimmed))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _normalize_embedding(values: list[float]) -> list[float]:
    return [float(value) for value in values]


def _build_fts_query(query: str) -> str:
    terms = re.findall(r"[\w\u4e00-\u9fff-]+", query.lower())
    if not terms:
        return ""
    return " OR ".join(f'"{term}"' for term in terms)


class SQLiteBackend:
    def __init__(self, database_path: str = ":memory:", prefer_sqlite_vec: bool = True) -> None:
        self.database_path = database_path
        self.prefer_sqlite_vec = prefer_sqlite_vec
        self.connection = sqlite3.connect(database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        if database_path != ":memory:":
            self.connection.execute("PRAGMA journal_mode = WAL")
        self._sqlite_vec = None
        self._sqlite_vec_enabled = False
        self._bootstrap()
        if self.prefer_sqlite_vec:
            self._try_enable_sqlite_vec()

    def _bootstrap(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        self.connection.executescript(schema_path.read_text())
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def add_memory(self, item: MemoryItem) -> MemoryItem:
        payload = self._memory_to_row(item)
        cursor = self.connection.execute(
            """
            INSERT INTO memories (
                id, content, memory_type, created_at, last_accessed, access_count,
                valid_from, valid_until, trust_score, importance, layer, decay_rate,
                source_id, causal_parent_id, supersedes_id, entity_refs_json, tags_json, deleted_at
            ) VALUES (
                :id, :content, :memory_type, :created_at, :last_accessed, :access_count,
                :valid_from, :valid_until, :trust_score, :importance, :layer, :decay_rate,
                :source_id, :causal_parent_id, :supersedes_id, :entity_refs_json, :tags_json, :deleted_at
            )
            """,
            payload,
        )
        memory_rowid = int(cursor.lastrowid)
        self.connection.execute(
            "INSERT INTO memory_vectors (memory_id, memory_rowid, embedding_json) VALUES (?, ?, ?)",
            (item.id, memory_rowid, json.dumps(_normalize_embedding(item.embedding))),
        )
        self.connection.executemany(
            "INSERT OR IGNORE INTO entity_index (entity, memory_id) VALUES (?, ?)",
            [(entity.lower(), item.id) for entity in item.entity_refs],
        )
        self._upsert_vec_index_row(item=item, memory_rowid=memory_rowid)
        self._append_evolution(item.id, "created", {"source_id": item.source_id})
        self._append_audit("system", "create", "memory", item.id, {"source_id": item.source_id})
        self.connection.commit()
        return item

    def get_memory(self, memory_id: str) -> MemoryItem | None:
        row = self.connection.execute(
            """
            SELECT m.*, v.embedding_json
            FROM memories m
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            WHERE m.id = ?
            """,
            (memory_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_memory(row)

    def update_memory(self, item: MemoryItem) -> MemoryItem:
        payload = self._memory_to_row(item)
        self.connection.execute(
            """
            UPDATE memories SET
                content = :content,
                memory_type = :memory_type,
                created_at = :created_at,
                last_accessed = :last_accessed,
                access_count = :access_count,
                valid_from = :valid_from,
                valid_until = :valid_until,
                trust_score = :trust_score,
                importance = :importance,
                layer = :layer,
                decay_rate = :decay_rate,
                source_id = :source_id,
                causal_parent_id = :causal_parent_id,
                supersedes_id = :supersedes_id,
                entity_refs_json = :entity_refs_json,
                tags_json = :tags_json,
                deleted_at = :deleted_at
            WHERE id = :id
            """,
            payload,
        )
        self.connection.execute(
            "UPDATE memory_vectors SET embedding_json = ? WHERE memory_id = ?",
            (json.dumps(_normalize_embedding(item.embedding)), item.id),
        )
        self.connection.execute("DELETE FROM entity_index WHERE memory_id = ?", (item.id,))
        self.connection.executemany(
            "INSERT OR IGNORE INTO entity_index (entity, memory_id) VALUES (?, ?)",
            [(entity.lower(), item.id) for entity in item.entity_refs],
        )
        row = self.connection.execute(
            "SELECT memory_rowid FROM memory_vectors WHERE memory_id = ?",
            (item.id,),
        ).fetchone()
        if row is not None:
            self._delete_vec_index_row(int(row["memory_rowid"]))
            self._upsert_vec_index_row(item=item, memory_rowid=int(row["memory_rowid"]))
        self._append_evolution(item.id, "updated", {"source_id": item.source_id})
        self._append_audit("system", "update", "memory", item.id, {"source_id": item.source_id})
        self.connection.commit()
        return item

    def soft_delete_memory(self, memory_id: str) -> bool:
        deleted_at = _utcnow_iso()
        cursor = self.connection.execute(
            "UPDATE memories SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (deleted_at, memory_id),
        )
        if cursor.rowcount == 0:
            return False
        row = self.connection.execute(
            "SELECT memory_rowid FROM memory_vectors WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        if row is not None:
            self._delete_vec_index_row(int(row["memory_rowid"]))
        self._append_evolution(memory_id, "deleted", {"deleted_at": deleted_at})
        self._append_audit("system", "delete", "memory", memory_id, {"deleted_at": deleted_at})
        self.connection.commit()
        return True

    def touch_memory(self, memory_id: str) -> None:
        accessed_at = _utcnow_iso()
        self.connection.execute(
            """
            UPDATE memories
            SET access_count = access_count + 1,
                last_accessed = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (accessed_at, memory_id),
        )
        self.connection.commit()

    def search_full_text(self, query: str, limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        fts_query = _build_fts_query(query)
        if not fts_query:
            return []
        params: list[object] = [fts_query]
        memory_type_clause = ""
        if memory_type:
            memory_type_clause = "AND m.memory_type = ?"
            params.append(memory_type)
        params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT m.*, v.embedding_json, bm25(memories_fts) AS rank_score
            FROM memories_fts
            JOIN memories m ON m.rowid = memories_fts.rowid
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            WHERE memories_fts MATCH ?
              AND m.deleted_at IS NULL
              {memory_type_clause}
            ORDER BY rank_score
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [(self._row_to_memory(row), 1.0 / (1.0 + abs(row["rank_score"]))) for row in rows]

    def search_by_entities(self, entities: list[str], limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        if not entities:
            return []
        placeholders = ", ".join("?" for _ in entities)
        params: list[object] = [entity.lower() for entity in entities]
        memory_type_clause = ""
        if memory_type:
            memory_type_clause = "AND m.memory_type = ?"
            params.append(memory_type)
        params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT m.*, v.embedding_json, COUNT(*) AS entity_hits
            FROM entity_index e
            JOIN memories m ON m.id = e.memory_id
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            WHERE e.entity IN ({placeholders})
              AND m.deleted_at IS NULL
              {memory_type_clause}
            GROUP BY m.id
            ORDER BY entity_hits DESC, m.created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [(self._row_to_memory(row), float(row["entity_hits"])) for row in rows]

    def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        if self._sqlite_vec_enabled:
            results = self._search_by_vector_sqlite_vec(embedding=embedding, limit=limit, memory_type=memory_type)
            if results:
                return results
        return self._search_by_vector_fallback(embedding=embedding, limit=limit, memory_type=memory_type)

    def _search_by_vector_fallback(
        self,
        embedding: list[float],
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        params: list[object] = []
        memory_type_clause = ""
        if memory_type:
            memory_type_clause = "AND m.memory_type = ?"
            params.append(memory_type)
        rows = self.connection.execute(
            f"""
            SELECT m.*, v.embedding_json
            FROM memories m
            JOIN memory_vectors v ON v.memory_id = m.id
            WHERE m.deleted_at IS NULL
              {memory_type_clause}
            """,
            params,
        ).fetchall()
        scored = []
        for row in rows:
            stored_embedding = json.loads(row["embedding_json"])
            score = _cosine_similarity(embedding, stored_embedding)
            scored.append((self._row_to_memory(row), score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def _search_by_vector_sqlite_vec(
        self,
        embedding: list[float],
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        serialized = self._serialize_embedding(embedding)
        if serialized is None:
            return []
        params: list[Any] = [serialized, limit]
        memory_type_clause = ""
        if memory_type:
            memory_type_clause = "AND v.memory_type = ?"
            params.append(memory_type)
        rows = self.connection.execute(
            f"""
            SELECT
                m.*,
                mv.embedding_json,
                v.distance AS vec_distance
            FROM memory_vec_index v
            JOIN memories m ON m.rowid = v.memory_rowid
            JOIN memory_vectors mv ON mv.memory_id = m.id
            WHERE v.embedding MATCH ?
              AND k = ?
              {memory_type_clause}
              AND m.deleted_at IS NULL
            ORDER BY v.distance ASC
            """,
            params,
        ).fetchall()
        return [(self._row_to_memory(row), 1.0 / (1.0 + float(row["vec_distance"]))) for row in rows]

    def trace_ancestors(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        rows = self.connection.execute(
            """
            WITH RECURSIVE ancestors(id, depth) AS (
                SELECT causal_parent_id, 1
                FROM memories
                WHERE id = ? AND causal_parent_id IS NOT NULL
                UNION ALL
                SELECT m.causal_parent_id, a.depth + 1
                FROM ancestors a
                JOIN memories m ON m.id = a.id
                WHERE a.depth < ? AND m.causal_parent_id IS NOT NULL
            )
            SELECT m.*, v.embedding_json, a.depth
            FROM ancestors a
            JOIN memories m ON m.id = a.id
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            WHERE m.deleted_at IS NULL
            ORDER BY a.depth ASC
            """,
            (memory_id, max_depth),
        ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def list_memories(self, include_deleted: bool = False) -> list[MemoryItem]:
        deleted_clause = "" if include_deleted else "WHERE m.deleted_at IS NULL"
        rows = self.connection.execute(
            f"""
            SELECT m.*, v.embedding_json
            FROM memories m
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            {deleted_clause}
            ORDER BY m.created_at DESC
            """
        ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def add_relation(self, edge: RelationEdge) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO relations (source_id, target_id, relation_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                edge.source_id,
                edge.target_id,
                edge.relation_type.value,
                _serialize_datetime(edge.created_at),
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_relations(self, memory_id: str | None = None) -> list[RelationEdge]:
        if memory_id is None:
            rows = self.connection.execute(
                "SELECT source_id, target_id, relation_type, created_at FROM relations ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT source_id, target_id, relation_type, created_at
                FROM relations
                WHERE source_id = ? OR target_id = ?
                ORDER BY created_at DESC
                """,
                (memory_id, memory_id),
            ).fetchall()
        return [
            RelationEdge(
                source_id=row["source_id"],
                target_id=row["target_id"],
                relation_type=RelationType(row["relation_type"]),
                created_at=_deserialize_datetime(row["created_at"]) or datetime.now(timezone.utc),
            )
            for row in rows
        ]

    def trace_descendants(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        rows = self.connection.execute(
            """
            WITH RECURSIVE descendants(id, depth) AS (
                SELECT id, 1
                FROM memories
                WHERE causal_parent_id = ?
                UNION ALL
                SELECT m.id, d.depth + 1
                FROM descendants d
                JOIN memories m ON m.causal_parent_id = d.id
                WHERE d.depth < ?
            )
            SELECT m.*, v.embedding_json, d.depth
            FROM descendants d
            JOIN memories m ON m.id = d.id
            LEFT JOIN memory_vectors v ON v.memory_id = m.id
            WHERE m.deleted_at IS NULL
            ORDER BY d.depth ASC, m.created_at ASC
            """,
            (memory_id, max_depth),
        ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def relation_exists_between(
        self,
        left_id: str,
        right_id: str,
        relation_types: list[str] | None = None,
    ) -> bool:
        if relation_types:
            placeholders = ", ".join("?" for _ in relation_types)
            row = self.connection.execute(
                f"""
                SELECT 1
                FROM relations
                WHERE ((source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?))
                  AND relation_type IN ({placeholders})
                LIMIT 1
                """,
                (left_id, right_id, right_id, left_id, *relation_types),
            ).fetchone()
        else:
            row = self.connection.execute(
                """
                SELECT 1
                FROM relations
                WHERE ((source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?))
                LIMIT 1
                """,
                (left_id, right_id, right_id, left_id),
            ).fetchone()
        return row is not None

    def get_evolution_events(self, memory_id: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        if memory_id is None:
            rows = self.connection.execute(
                """
                SELECT memory_id, event_type, payload_json, created_at
                FROM evolution_log
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT memory_id, event_type, payload_json, created_at
                FROM evolution_log
                WHERE memory_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (memory_id, limit),
            ).fetchall()
        return [
            {
                "memory_id": row["memory_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_audit_events(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute(
            """
            SELECT actor, operation, target_type, target_id, payload_json, created_at
            FROM audit_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "actor": row["actor"],
                "operation": row["operation"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def health_snapshot(self) -> dict[str, float | int]:
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS total_memories,
                SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END) AS active_memories,
                AVG(CASE WHEN deleted_at IS NULL THEN trust_score END) AS average_trust_score,
                SUM(
                    CASE
                        WHEN deleted_at IS NULL
                         AND julianday('now') - julianday(last_accessed) > 30
                        THEN 1 ELSE 0
                    END
                ) AS stale_memories
            FROM memories
            """
        ).fetchone()
        orphan_row = self.connection.execute(
            """
            SELECT COUNT(*) AS orphan_memories
            FROM memories m
            WHERE m.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM relations r
                  WHERE r.source_id = m.id OR r.target_id = m.id
              )
              AND m.access_count <= 1
            """
        ).fetchone()
        conflict_row = self.connection.execute(
            """
            SELECT COUNT(*) AS unresolved_conflicts
            FROM relations
            WHERE relation_type = 'contradicts'
            """
        ).fetchone()
        audit_row = self.connection.execute("SELECT COUNT(*) AS audit_events FROM audit_log").fetchone()
        total = int(row["active_memories"] or 0)
        stale = int(row["stale_memories"] or 0)
        orphan = int(orphan_row["orphan_memories"] or 0)
        return {
            "total_memories": total,
            "stale_ratio": (stale / total) if total else 0.0,
            "orphan_ratio": (orphan / total) if total else 0.0,
            "unresolved_conflicts": int(conflict_row["unresolved_conflicts"] or 0),
            "average_trust_score": float(row["average_trust_score"] or 0.0),
            "audit_events": int(audit_row["audit_events"] or 0),
        }

    def _append_evolution(self, memory_id: str, event_type: str, payload: dict[str, object]) -> None:
        self.connection.execute(
            "INSERT INTO evolution_log (memory_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (memory_id, event_type, json.dumps(payload), _utcnow_iso()),
        )

    def _append_audit(
        self,
        actor: str,
        operation: str,
        target_type: str,
        target_id: str,
        payload: dict[str, object],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_log (actor, operation, target_type, target_id, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor, operation, target_type, target_id, json.dumps(payload), _utcnow_iso()),
        )

    def _memory_to_row(self, item: MemoryItem) -> dict[str, object]:
        return {
            "id": item.id,
            "content": item.content,
            "memory_type": item.memory_type.value,
            "created_at": _serialize_datetime(item.created_at),
            "last_accessed": _serialize_datetime(item.last_accessed),
            "access_count": item.access_count,
            "valid_from": _serialize_datetime(item.valid_from),
            "valid_until": _serialize_datetime(item.valid_until),
            "trust_score": item.trust_score,
            "importance": item.importance,
            "layer": item.layer.value,
            "decay_rate": item.decay_rate,
            "source_id": item.source_id,
            "causal_parent_id": item.causal_parent_id,
            "supersedes_id": item.supersedes_id,
            "entity_refs_json": json.dumps(item.entity_refs),
            "tags_json": json.dumps(item.tags),
            "deleted_at": _serialize_datetime(item.deleted_at),
        }

    def _row_to_memory(self, row: sqlite3.Row) -> MemoryItem:
        embedding_json = row["embedding_json"] if "embedding_json" in row.keys() else "[]"
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            embedding=json.loads(embedding_json or "[]"),
            created_at=_deserialize_datetime(row["created_at"]) or datetime.now(timezone.utc),
            last_accessed=_deserialize_datetime(row["last_accessed"]) or datetime.now(timezone.utc),
            access_count=row["access_count"],
            valid_from=_deserialize_datetime(row["valid_from"]),
            valid_until=_deserialize_datetime(row["valid_until"]),
            trust_score=row["trust_score"],
            importance=row["importance"],
            layer=MemoryLayer(row["layer"]),
            decay_rate=row["decay_rate"],
            source_id=row["source_id"],
            causal_parent_id=row["causal_parent_id"],
            supersedes_id=row["supersedes_id"],
            entity_refs=json.loads(row["entity_refs_json"]),
            tags=json.loads(row["tags_json"]),
            deleted_at=_deserialize_datetime(row["deleted_at"]),
        )

    def _try_enable_sqlite_vec(self) -> None:
        try:
            sqlite_vec = importlib.import_module("sqlite_vec")
        except ImportError:
            return
        load = getattr(sqlite_vec, "load", None)
        if load is None:
            return
        try:
            load(self.connection)
        except Exception:
            return
        self._sqlite_vec = sqlite_vec
        self._sqlite_vec_enabled = True
        dimension = self._get_backend_meta("sqlite_vec_dimension")
        if dimension:
            self._ensure_vec_index_table(int(dimension))
            self._rebuild_vec_index_if_needed()

    def _serialize_embedding(self, embedding: list[float]) -> bytes | None:
        if not self._sqlite_vec_enabled or self._sqlite_vec is None:
            return None
        serializer = getattr(self._sqlite_vec, "serialize_float32", None)
        if serializer is None:
            return None
        return serializer(_normalize_embedding(embedding))

    def _ensure_vec_index_table(self, dimension: int) -> None:
        current_dimension = self._get_backend_meta("sqlite_vec_dimension")
        if current_dimension and int(current_dimension) != dimension:
            raise ValueError(
                f"sqlite-vec index dimension mismatch: existing={current_dimension}, requested={dimension}"
            )
        self.connection.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec_index
            USING vec0(
                memory_rowid INTEGER PRIMARY KEY,
                embedding FLOAT[{dimension}],
                memory_type TEXT,
                layer TEXT,
                source_id TEXT,
                trust_score FLOAT,
                created_at TEXT,
                last_accessed TEXT
            )
            """
        )
        self._set_backend_meta("sqlite_vec_dimension", str(dimension))

    def _upsert_vec_index_row(self, item: MemoryItem, memory_rowid: int) -> None:
        if not self._sqlite_vec_enabled:
            return
        serialized = self._serialize_embedding(item.embedding)
        if serialized is None:
            return
        self._ensure_vec_index_table(len(item.embedding))
        update_cursor = self.connection.execute(
            """
            UPDATE memory_vec_index
            SET embedding = ?, memory_type = ?, layer = ?, source_id = ?, trust_score = ?, created_at = ?, last_accessed = ?
            WHERE memory_rowid = ?
            """,
            (
                serialized,
                item.memory_type.value,
                item.layer.value,
                item.source_id,
                item.trust_score,
                _serialize_datetime(item.created_at),
                _serialize_datetime(item.last_accessed),
                memory_rowid,
            ),
        )
        if update_cursor.rowcount > 0:
            return
        self.connection.execute(
            """
            INSERT INTO memory_vec_index (
                memory_rowid, embedding, memory_type, layer, source_id, trust_score, created_at, last_accessed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_rowid,
                serialized,
                item.memory_type.value,
                item.layer.value,
                item.source_id,
                item.trust_score,
                _serialize_datetime(item.created_at),
                _serialize_datetime(item.last_accessed),
            ),
        )

    def _delete_vec_index_row(self, memory_rowid: int) -> None:
        if not self._sqlite_vec_enabled:
            return
        self.connection.execute("DELETE FROM memory_vec_index WHERE memory_rowid = ?", (memory_rowid,))

    def _rebuild_vec_index_if_needed(self) -> None:
        if not self._sqlite_vec_enabled:
            return
        count_row = self.connection.execute("SELECT COUNT(*) AS count FROM memory_vec_index").fetchone()
        existing_count = int(count_row["count"] or 0)
        memory_rows = self.connection.execute(
            """
            SELECT
                m.rowid AS memory_rowid,
                m.*,
                mv.embedding_json
            FROM memories m
            JOIN memory_vectors mv ON mv.memory_id = m.id
            WHERE m.deleted_at IS NULL
            """
        ).fetchall()
        if existing_count >= len(memory_rows):
            return
        self.connection.execute("DELETE FROM memory_vec_index")
        for row in memory_rows:
            item = self._row_to_memory(row)
            self._upsert_vec_index_row(item=item, memory_rowid=int(row["memory_rowid"]))
        self.connection.commit()

    def _get_backend_meta(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM backend_meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def _set_backend_meta(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO backend_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
