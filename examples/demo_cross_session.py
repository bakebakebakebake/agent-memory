from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_memory import ConversationTurn, MemoryClient
from agent_memory.config import AgentMemoryConfig


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def dump_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def build_client(db_path: str) -> MemoryClient:
    return MemoryClient(config=AgentMemoryConfig(database_path=db_path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-interactive cross-session demo for agent-memory.")
    parser.add_argument("--db", default="demo_cross_session.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()

    print_section("1. Create client and store initial memories")
    client = build_client(str(db_path))
    session_1 = "session-001"
    created = client.ingest_conversation(
        [
            ConversationTurn(role="user", content="我是张三，是一名后端工程师，主要使用 Go 和 Python。"),
            ConversationTurn(role="user", content="我最近在学习 Rust，因为我想做更底层的系统工具。"),
            ConversationTurn(role="user", content="我偏好 SQLite，因为它零配置，本地演示和集成都很方便。"),
        ],
        source_id=session_1,
    )
    dump_json([{"id": item.id, "content": item.content, "trust_score": item.trust_score} for item in created])

    print_section("2. Intent-aware search")
    for query in [
        "张三的职业是什么？",
        "为什么他偏好 SQLite？",
        "最近在学习什么？",
    ]:
        results = client.search(query, limit=3)
        print(f"Query: {query}")
        dump_json([{"content": result.item.content, "matched_by": result.matched_by} for result in results])

    print_section("3. Add conflicting information")
    conflict = client.add(
        "张三现在主要转向 Rust，不再把 Python 作为主力语言。",
        source_id="session-002",
        tags=["conflict-demo"],
    )
    dump_json({"id": conflict.id, "content": conflict.content, "trust_score": conflict.trust_score})

    print_section("4. Trace graph")
    trace = client.trace_graph(created[0].id)
    dump_json(
        {
            "focus": trace.focus.content,
            "ancestors": [item.content for item in trace.ancestors],
            "descendants": [item.content for item in trace.descendants],
            "relations": [edge.relation_type.value for edge in trace.relations],
        }
    )

    print_section("5. Maintenance and health")
    maintenance = client.maintain()
    health = client.health()
    dump_json({"maintenance": maintenance, "health": health})

    print_section("6. Export and import")
    with TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "memories.jsonl"
        imported_db = Path(tmpdir) / "imported.db"
        exported = client.export_jsonl(str(export_path))
        print(f"Exported {exported} records to {export_path}")
        imported_client = build_client(str(imported_db))
        imported = imported_client.import_jsonl(str(export_path))
        print(f"Imported {imported} records into {imported_db}")
        print("Imported health:")
        dump_json(imported_client.health())

    print_section("7. Cross-session persistence")
    reloaded_client = build_client(str(db_path))
    results = reloaded_client.search("你还记得我是谁吗？", limit=5)
    dump_json([{"content": result.item.content, "score": result.score} for result in results])
    print(f"\nDemo complete. Persistent DB kept at: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
