from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class AgentMemoryConfig:
    database_path: str = str(Path.cwd() / "agent-memory.db")
    mode: str = "embedded"
    go_server_url: str = "http://127.0.0.1:8080"
    grpc_target: str = "127.0.0.1:9090"
    prefer_grpc: bool = True
    api_key: str | None = None
    jwt_token: str | None = None
    request_timeout_seconds: float = 5.0
    semantic_limit: int = 10
    lexical_limit: int = 10
    entity_limit: int = 10
    default_search_limit: int = 5
    rrf_k: int = 60
    enable_sqlite_vec: bool = True

    @classmethod
    def from_env(cls) -> "AgentMemoryConfig":
        return cls(
            database_path=os.getenv("AGENT_MEMORY_DB_PATH", str(Path.cwd() / "agent-memory.db")),
            mode=os.getenv("AGENT_MEMORY_MODE", "embedded"),
            go_server_url=os.getenv("AGENT_MEMORY_GO_SERVER_URL", "http://127.0.0.1:8080"),
            grpc_target=os.getenv("AGENT_MEMORY_GRPC_TARGET", "127.0.0.1:9090"),
            prefer_grpc=os.getenv("AGENT_MEMORY_PREFER_GRPC", "true").lower() not in {"0", "false", "no"},
            api_key=os.getenv("AGENT_MEMORY_API_KEY") or None,
            jwt_token=os.getenv("AGENT_MEMORY_JWT_TOKEN") or None,
            request_timeout_seconds=float(os.getenv("AGENT_MEMORY_REQUEST_TIMEOUT_SECONDS", "5.0")),
            semantic_limit=int(os.getenv("AGENT_MEMORY_SEMANTIC_LIMIT", "10")),
            lexical_limit=int(os.getenv("AGENT_MEMORY_LEXICAL_LIMIT", "10")),
            entity_limit=int(os.getenv("AGENT_MEMORY_ENTITY_LIMIT", "10")),
            default_search_limit=int(os.getenv("AGENT_MEMORY_DEFAULT_SEARCH_LIMIT", "5")),
            rrf_k=int(os.getenv("AGENT_MEMORY_RRF_K", "60")),
            enable_sqlite_vec=os.getenv("AGENT_MEMORY_ENABLE_SQLITE_VEC", "true").lower() not in {"0", "false", "no"},
        )
