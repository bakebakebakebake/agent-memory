from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass, replace
from enum import Enum
import json
from pathlib import Path
from typing import Any

from agent_memory.client import MemoryClient
from agent_memory.config import AgentMemoryConfig


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-memory", description="Zero-config local memory engine for agents.")
    parser.add_argument("--db", dest="database_path", help="Path to the SQLite database file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    store = subparsers.add_parser("store", help="Store a memory.")
    store.add_argument("content")
    store.add_argument("--source-id", default="cli")
    store.add_argument("--memory-type", default="semantic")
    store.add_argument("--causal-parent-id")
    store.add_argument("--tag", action="append", default=[])

    search = subparsers.add_parser("search", help="Search memories.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)

    trace = subparsers.add_parser("trace", help="Trace a memory graph.")
    trace.add_argument("memory_id")
    trace.add_argument("--max-depth", type=int, default=10)

    evolution = subparsers.add_parser("evolution", help="Show memory evolution history.")
    evolution.add_argument("memory_id")
    evolution.add_argument("--limit", type=int, default=20)

    audit = subparsers.add_parser("audit", help="Show recent audit events.")
    audit.add_argument("--limit", type=int, default=20)

    health = subparsers.add_parser("health", help="Show memory health report.")

    maintain = subparsers.add_parser("maintain", help="Run maintenance cycle.")

    export_cmd = subparsers.add_parser("export", help="Export to JSONL.")
    export_cmd.add_argument("path")

    import_cmd = subparsers.add_parser("import", help="Import from JSONL.")
    import_cmd.add_argument("path")

    return parser


def _build_client(database_path: str | None) -> MemoryClient:
    config = AgentMemoryConfig.from_env()
    if database_path:
        config = replace(config, database_path=database_path)
    return MemoryClient(config=config)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = _build_client(args.database_path)
    try:
        if args.command == "store":
            item = client.add(
                args.content,
                source_id=args.source_id,
                memory_type=args.memory_type,
                causal_parent_id=args.causal_parent_id,
                tags=list(args.tag),
            )
            _print_json({"id": item.id, "content": item.content, "trust_score": item.trust_score})
            return 0

        if args.command == "search":
            _print_json(
                [
                    {
                        "id": result.item.id,
                        "content": result.item.content,
                        "score": result.score,
                        "matched_by": result.matched_by,
                    }
                    for result in client.search(args.query, limit=args.limit)
                ]
            )
            return 0

        if args.command == "trace":
            _print_json(asdict(client.trace_graph(args.memory_id, max_depth=args.max_depth)))
            return 0

        if args.command == "evolution":
            _print_json(client.evolution_events(memory_id=args.memory_id, limit=args.limit))
            return 0

        if args.command == "audit":
            _print_json(client.audit_events(limit=args.limit))
            return 0

        if args.command == "health":
            _print_json(asdict(client.health()))
            return 0

        if args.command == "maintain":
            _print_json(asdict(client.maintain()))
            return 0

        if args.command == "export":
            path = str(Path(args.path))
            _print_json({"path": path, "exported": client.export_jsonl(path)})
            return 0

        if args.command == "import":
            path = str(Path(args.path))
            _print_json({"path": path, "imported": client.import_jsonl(path)})
            return 0

        parser.error(f"Unsupported command: {args.command}")
        return 2
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
