from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from enum import Enum
import json
from typing import Any
from urllib import error, parse, request

from agent_memory.config import AgentMemoryConfig
from agent_memory.models import MemoryItem, MemoryLayer, MemoryType, RelationEdge, RelationType, SearchResult

try:
    import grpc  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    grpc = None

try:
    from agent_memory.generated.memory.v1 import models_pb2, storage_service_pb2, storage_service_pb2_grpc
except ImportError:  # pragma: no cover - generated later in setup
    models_pb2 = None
    storage_service_pb2 = None
    storage_service_pb2_grpc = None


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_json_default(item) for item in value]
    return value


def _memory_to_payload(item: MemoryItem) -> dict[str, object]:
    payload = asdict(item)
    return {key: _json_default(value) for key, value in payload.items()}


def _relation_to_payload(edge: RelationEdge) -> dict[str, object]:
    payload = asdict(edge)
    return {key: _json_default(value) for key, value in payload.items()}


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _memory_from_payload(payload: dict[str, Any]) -> MemoryItem:
    return MemoryItem(
        id=str(payload["id"]),
        content=str(payload["content"]),
        memory_type=MemoryType(payload["memory_type"]),
        embedding=[float(value) for value in payload.get("embedding", [])],
        created_at=_parse_datetime(payload.get("created_at")) or datetime.now().astimezone(),
        last_accessed=_parse_datetime(payload.get("last_accessed")) or datetime.now().astimezone(),
        access_count=int(payload.get("access_count", 0)),
        valid_from=_parse_datetime(payload.get("valid_from")),
        valid_until=_parse_datetime(payload.get("valid_until")),
        trust_score=float(payload.get("trust_score", 0.75)),
        importance=float(payload.get("importance", 0.5)),
        layer=MemoryLayer(payload.get("layer", MemoryLayer.SHORT_TERM.value)),
        decay_rate=float(payload.get("decay_rate", 0.1)),
        source_id=str(payload.get("source_id", "remote")),
        causal_parent_id=payload.get("causal_parent_id"),
        supersedes_id=payload.get("supersedes_id"),
        entity_refs=[str(value) for value in payload.get("entity_refs", [])],
        tags=[str(value) for value in payload.get("tags", [])],
        deleted_at=_parse_datetime(payload.get("deleted_at")),
    )


def _relation_from_payload(payload: dict[str, Any]) -> RelationEdge:
    return RelationEdge(
        source_id=str(payload["source_id"]),
        target_id=str(payload["target_id"]),
        relation_type=RelationType(payload["relation_type"]),
        created_at=_parse_datetime(payload.get("created_at")) or datetime.now().astimezone(),
    )


class RemoteBackend:
    def __init__(self, config: AgentMemoryConfig) -> None:
        self.config = config
        self.database_path = ":remote:"
        self._grpc_channel = None
        self._grpc_stub = None
        if self.config.prefer_grpc and grpc is not None and storage_service_pb2_grpc is not None:
            self._grpc_channel = grpc.insecure_channel(self.config.grpc_target)
            self._grpc_stub = storage_service_pb2_grpc.StorageServiceStub(self._grpc_channel)

    def close(self) -> None:
        if self._grpc_channel is not None:
            self._grpc_channel.close()

    def add_memory(self, item: MemoryItem) -> MemoryItem:
        if self._grpc_stub is not None:
            response = self._grpc_call("AddMemory", storage_service_pb2.AddMemoryRequest(item=self._memory_to_proto(item)))
            return self._memory_from_proto(response.item)
        payload = self._request_json("POST", "/api/v1/memories", data=_memory_to_payload(item))
        return _memory_from_payload(payload["item"])

    def get_memory(self, memory_id: str) -> MemoryItem | None:
        if self._grpc_stub is not None:
            response = self._grpc_call("GetMemory", storage_service_pb2.GetMemoryRequest(memory_id=memory_id))
            if not response.found:
                return None
            return self._memory_from_proto(response.item)
        payload = self._request_json("GET", f"/api/v1/memories/{memory_id}")
        if not payload.get("found", False):
            return None
        return _memory_from_payload(payload["item"])

    def update_memory(self, item: MemoryItem) -> MemoryItem:
        if self._grpc_stub is not None:
            response = self._grpc_call("UpdateMemory", storage_service_pb2.UpdateMemoryRequest(item=self._memory_to_proto(item)))
            return self._memory_from_proto(response.item)
        payload = self._request_json("PUT", f"/api/v1/memories/{item.id}", data=_memory_to_payload(item))
        return _memory_from_payload(payload["item"])

    def soft_delete_memory(self, memory_id: str) -> bool:
        if self._grpc_stub is not None:
            response = self._grpc_call("DeleteMemory", storage_service_pb2.DeleteMemoryRequest(memory_id=memory_id))
            return bool(response.deleted)
        payload = self._request_json("DELETE", f"/api/v1/memories/{memory_id}")
        return bool(payload["deleted"])

    def search_full_text(self, query: str, limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "SearchFullText",
                storage_service_pb2.SearchFullTextRequest(query=query, limit=limit, memory_type=memory_type or ""),
            )
            return [(self._memory_from_proto(result.item), float(result.score)) for result in response.results]
        payload = self._request_json(
            "POST",
            "/api/v1/search/full-text",
            data={"query": query, "limit": limit, "memory_type": memory_type},
        )
        return self._parse_search_results(payload["results"])

    def search_query(
        self,
        query: str,
        *,
        embedding: list[float],
        entities: list[str],
        limit: int = 5,
    ) -> list[SearchResult]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "SearchQuery",
                storage_service_pb2.SearchQueryRequest(
                    query=query,
                    embedding=embedding,
                    entities=entities,
                    limit=limit,
                ),
            )
            return [self._search_result_from_proto(result) for result in response.results]
        payload = self._request_json(
            "POST",
            "/api/v1/search/query",
            data={"query": query, "embedding": embedding, "entities": entities, "limit": limit},
        )
        return [self._search_result_from_payload(result) for result in payload["results"]]

    def search_by_entities(self, entities: list[str], limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "SearchByEntities",
                storage_service_pb2.SearchByEntitiesRequest(entities=entities, limit=limit, memory_type=memory_type or ""),
            )
            return [(self._memory_from_proto(result.item), float(result.score)) for result in response.results]
        payload = self._request_json(
            "POST",
            "/api/v1/search/entities",
            data={"entities": entities, "limit": limit, "memory_type": memory_type},
        )
        return self._parse_search_results(payload["results"])

    def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "SearchByVector",
                storage_service_pb2.SearchByVectorRequest(embedding=embedding, limit=limit, memory_type=memory_type or ""),
            )
            return [(self._memory_from_proto(result.item), float(result.score)) for result in response.results]
        payload = self._request_json(
            "POST",
            "/api/v1/search/vector",
            data={"embedding": embedding, "limit": limit, "memory_type": memory_type},
        )
        return self._parse_search_results(payload["results"])

    def touch_memory(self, memory_id: str) -> None:
        if self._grpc_stub is not None:
            self._grpc_call("TouchMemory", storage_service_pb2.TouchMemoryRequest(memory_id=memory_id))
            return
        self._request_json("POST", "/api/v1/touch", data={"memory_id": memory_id})

    def trace_ancestors(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "TraceAncestors",
                storage_service_pb2.TraceAncestorsRequest(memory_id=memory_id, max_depth=max_depth),
            )
            return [self._memory_from_proto(item) for item in response.items]
        payload = self._request_json("GET", f"/api/v1/trace/ancestors?memory_id={parse.quote(memory_id)}&max_depth={max_depth}")
        return [_memory_from_payload(item) for item in payload["items"]]

    def list_memories(self, include_deleted: bool = False) -> list[MemoryItem]:
        if self._grpc_stub is not None:
            response = self._grpc_call("ListMemories", storage_service_pb2.ListMemoriesRequest(include_deleted=include_deleted))
            return [self._memory_from_proto(item) for item in response.items]
        payload = self._request_json("GET", f"/api/v1/memories?include_deleted={'true' if include_deleted else 'false'}")
        return [_memory_from_payload(item) for item in payload["items"]]

    def add_relation(self, edge: RelationEdge) -> bool:
        if self._grpc_stub is not None:
            response = self._grpc_call("AddRelation", storage_service_pb2.AddRelationRequest(edge=self._relation_to_proto(edge)))
            return bool(response.created)
        payload = self._request_json("POST", "/api/v1/relations", data=_relation_to_payload(edge))
        return bool(payload["created"])

    def list_relations(self, memory_id: str | None = None) -> list[RelationEdge]:
        if self._grpc_stub is not None:
            response = self._grpc_call("ListRelations", storage_service_pb2.ListRelationsRequest(memory_id=memory_id or ""))
            return [self._relation_from_proto(edge) for edge in response.items]
        suffix = f"?memory_id={parse.quote(memory_id)}" if memory_id else ""
        payload = self._request_json("GET", f"/api/v1/relations{suffix}")
        return [_relation_from_payload(item) for item in payload["items"]]

    def trace_descendants(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "TraceDescendants",
                storage_service_pb2.TraceDescendantsRequest(memory_id=memory_id, max_depth=max_depth),
            )
            return [self._memory_from_proto(item) for item in response.items]
        payload = self._request_json("GET", f"/api/v1/trace/descendants?memory_id={parse.quote(memory_id)}&max_depth={max_depth}")
        return [_memory_from_payload(item) for item in payload["items"]]

    def relation_exists_between(
        self,
        left_id: str,
        right_id: str,
        relation_types: list[str] | None = None,
    ) -> bool:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "RelationExists",
                storage_service_pb2.RelationExistsRequest(left_id=left_id, right_id=right_id, relation_types=relation_types or []),
            )
            return bool(response.value)
        query = parse.urlencode(
            {"left_id": left_id, "right_id": right_id, "relation_types": ",".join(relation_types or [])}
        )
        payload = self._request_json("GET", f"/api/v1/relations/exists?{query}")
        return bool(payload["exists"])

    def get_evolution_events(self, memory_id: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        if self._grpc_stub is not None:
            response = self._grpc_call(
                "GetEvolutionEvents",
                storage_service_pb2.GetEvolutionEventsRequest(memory_id=memory_id or "", limit=limit),
            )
            return [self._evolution_from_proto(event) for event in response.items]
        query = parse.urlencode({"memory_id": memory_id or "", "limit": limit})
        payload = self._request_json("GET", f"/api/v1/evolution?{query}")
        return list(payload["items"])

    def get_audit_events(self, limit: int = 100) -> list[dict[str, object]]:
        if self._grpc_stub is not None:
            response = self._grpc_call("GetAuditEvents", storage_service_pb2.GetAuditEventsRequest(limit=limit))
            return [self._audit_from_proto(event) for event in response.items]
        payload = self._request_json("GET", f"/api/v1/audit?limit={limit}")
        return list(payload["items"])

    def health_snapshot(self) -> dict[str, float | int]:
        if self._grpc_stub is not None:
            response = self._grpc_call("HealthCheck", storage_service_pb2.HealthCheckRequest())
            return {
                "total_memories": int(response.snapshot.total_memories),
                "stale_ratio": float(response.snapshot.stale_ratio),
                "orphan_ratio": float(response.snapshot.orphan_ratio),
                "unresolved_conflicts": int(response.snapshot.unresolved_conflicts),
                "average_trust_score": float(response.snapshot.average_trust_score),
                "audit_events": int(response.snapshot.audit_events),
                "database_size_bytes": int(response.snapshot.database_size_bytes),
            }
        payload = self._request_json("GET", "/health")
        return {
            "total_memories": int(payload.get("total_memories", 0)),
            "stale_ratio": float(payload.get("stale_ratio", 0.0)),
            "orphan_ratio": float(payload.get("orphan_ratio", 0.0)),
            "unresolved_conflicts": int(payload.get("unresolved_conflicts", 0)),
            "average_trust_score": float(payload.get("average_trust_score", 0.0)),
            "audit_events": int(payload.get("audit_events", 0)),
            "database_size_bytes": int(payload.get("database_size_bytes", 0)),
        }

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.config.go_server_url.rstrip('/')}{path}"
        payload = None
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        if self.config.jwt_token:
            headers["Authorization"] = f"Bearer {self.config.jwt_token}"
        if data is not None:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = request.Request(url, data=payload, method=method, headers=headers)
        try:
            with request.urlopen(req, timeout=self.config.request_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - exercised in integration
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Remote backend request failed: {exc.code} {detail}") from exc

    def _grpc_call(self, method_name: str, request_message):
        if self._grpc_stub is None:
            raise RuntimeError("gRPC stub is unavailable")
        metadata: list[tuple[str, str]] = []
        if self.config.api_key:
            metadata.append(("x-api-key", self.config.api_key))
        if self.config.jwt_token:
            metadata.append(("authorization", f"Bearer {self.config.jwt_token}"))
        method = getattr(self._grpc_stub, method_name)
        return method(request_message, metadata=metadata or None)

    def _parse_search_results(self, results: list[dict[str, object]]) -> list[tuple[MemoryItem, float]]:
        parsed: list[tuple[MemoryItem, float]] = []
        for item in results:
            parsed.append((_memory_from_payload(item["item"]), float(item["score"])))
        return parsed

    def _search_result_from_payload(self, payload: dict[str, object]) -> SearchResult:
        return SearchResult(
            item=_memory_from_payload(payload["item"]),
            score=float(payload["score"]),
            matched_by=[str(value) for value in payload.get("matched_by", [])],
        )

    def _memory_to_proto(self, item: MemoryItem):
        if models_pb2 is None:
            raise RuntimeError("gRPC stubs are unavailable. Install remote dependencies and regenerate protos.")
        return models_pb2.MemoryItem(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type.value,
            embedding=item.embedding,
            created_at=item.created_at.isoformat(),
            last_accessed=item.last_accessed.isoformat(),
            access_count=item.access_count,
            valid_from=item.valid_from.isoformat() if item.valid_from else "",
            valid_until=item.valid_until.isoformat() if item.valid_until else "",
            trust_score=item.trust_score,
            importance=item.importance,
            layer=item.layer.value,
            decay_rate=item.decay_rate,
            source_id=item.source_id,
            causal_parent_id=item.causal_parent_id or "",
            supersedes_id=item.supersedes_id or "",
            entity_refs=item.entity_refs,
            tags=item.tags,
            deleted_at=item.deleted_at.isoformat() if item.deleted_at else "",
        )

    def _memory_from_proto(self, item) -> MemoryItem:
        return _memory_from_payload(
            {
                "id": item.id,
                "content": item.content,
                "memory_type": item.memory_type,
                "embedding": list(item.embedding),
                "created_at": item.created_at,
                "last_accessed": item.last_accessed,
                "access_count": item.access_count,
                "valid_from": item.valid_from or None,
                "valid_until": item.valid_until or None,
                "trust_score": item.trust_score,
                "importance": item.importance,
                "layer": item.layer,
                "decay_rate": item.decay_rate,
                "source_id": item.source_id,
                "causal_parent_id": item.causal_parent_id or None,
                "supersedes_id": item.supersedes_id or None,
                "entity_refs": list(item.entity_refs),
                "tags": list(item.tags),
                "deleted_at": item.deleted_at or None,
            }
        )

    def _relation_to_proto(self, edge: RelationEdge):
        if models_pb2 is None:
            raise RuntimeError("gRPC stubs are unavailable. Install remote dependencies and regenerate protos.")
        return models_pb2.RelationEdge(
            source_id=edge.source_id,
            target_id=edge.target_id,
            relation_type=edge.relation_type.value,
            created_at=edge.created_at.isoformat(),
        )

    def _relation_from_proto(self, edge) -> RelationEdge:
        return _relation_from_payload(
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "created_at": edge.created_at,
            }
        )

    def _evolution_from_proto(self, event) -> dict[str, object]:
        payload = json.loads(event.payload_json) if event.payload_json else {}
        return {
            "memory_id": event.memory_id,
            "event_type": event.event_type,
            "payload": payload,
            "created_at": event.created_at,
        }

    def _audit_from_proto(self, event) -> dict[str, object]:
        payload = json.loads(event.payload_json) if event.payload_json else {}
        return {
            "actor": event.actor,
            "operation": event.operation,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "payload": payload,
            "created_at": event.created_at,
        }

    def _search_result_from_proto(self, result) -> SearchResult:
        return SearchResult(
            item=self._memory_from_proto(result.item),
            score=float(result.score),
            matched_by=[str(value) for value in result.matched_by],
        )
