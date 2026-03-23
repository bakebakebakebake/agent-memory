from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class AgentMemoryConfig:
    database_path: str = str(Path.cwd() / "agent-memory.db")
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
            semantic_limit=int(os.getenv("AGENT_MEMORY_SEMANTIC_LIMIT", "10")),
            lexical_limit=int(os.getenv("AGENT_MEMORY_LEXICAL_LIMIT", "10")),
            entity_limit=int(os.getenv("AGENT_MEMORY_ENTITY_LIMIT", "10")),
            default_search_limit=int(os.getenv("AGENT_MEMORY_DEFAULT_SEARCH_LIMIT", "5")),
            rrf_k=int(os.getenv("AGENT_MEMORY_RRF_K", "60")),
            enable_sqlite_vec=os.getenv("AGENT_MEMORY_ENABLE_SQLITE_VEC", "true").lower() not in {"0", "false", "no"},
        )
