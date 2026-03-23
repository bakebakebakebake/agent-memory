from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_memory import ConversationTurn, MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.llm.ollama_client import OllamaClient
from agent_memory.llm.openai_client import OpenAIClient


def build_llm(provider: str):
    if provider == "openai":
        return OpenAIClient()
    if provider == "ollama":
        return OllamaClient()
    return None


def generate_reply(client: MemoryClient, user_text: str, provider: str) -> str:
    memories = client.search(user_text, limit=5)
    memory_context = "\n".join(f"- {result.item.content}" for result in memories) or "- No relevant memories yet."
    llm = build_llm(provider)
    if llm is None:
        if memories:
            return f"我记得这些相关信息：{'; '.join(result.item.content for result in memories[:3])}"
        return "我会把这条信息记下来。"

    prompt = (
        "You are a memory-augmented assistant. Reply in the user's language.\n"
        f"Relevant memories:\n{memory_context}\n"
        f"User message: {user_text}"
    )
    try:
        return llm.complete(prompt)
    except Exception as exc:
        if memories:
            return f"LLM 不可用({exc})，但我记得：{'; '.join(result.item.content for result in memories[:3])}"
        return f"LLM 不可用({exc})，不过我已经把这条信息记住了。"


def show_help() -> None:
    print("Commands:")
    print("  /help                 Show this help")
    print("  /memories             List current memories")
    print("  /trace <memory_id>    Show memory trace")
    print("  /health               Show health report")
    print("  /search <query>       Search memories")
    print("  /quit                 Exit")


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive chatbot demo backed by agent-memory.")
    parser.add_argument("--db", default="chat_memory.db")
    parser.add_argument("--provider", choices=["none", "openai", "ollama"], default="none")
    args = parser.parse_args()

    client = MemoryClient(config=AgentMemoryConfig(database_path=args.db))
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    print("🧠 Agent Memory Chat (type /help for commands)")
    print(f"Session: {session_id}")
    while True:
        try:
            user_text = input("\nYou: ").strip()
        except EOFError:
            print("\nGoodbye!")
            return 0

        if not user_text:
            continue
        if user_text == "/help":
            show_help()
            continue
        if user_text == "/quit":
            print(f"Goodbye! Memory persisted to {args.db}")
            return 0
        if user_text == "/memories":
            memories = client.backend.list_memories()
            print(f"📋 当前记忆 ({len(memories)} 条):")
            for index, memory in enumerate(memories[:10], start=1):
                print(f"  {index}. [{memory.memory_type.value}] {memory.content} (trust: {memory.trust_score:.2f})")
            continue
        if user_text.startswith("/trace "):
            memory_id = user_text.split(maxsplit=1)[1]
            try:
                trace = client.trace_graph(memory_id)
            except Exception as exc:
                print(f"Bot: trace failed: {exc}")
                continue
            print("📊 记忆溯源:")
            print(f"  Focus: {trace.focus.content}")
            print(f"  来源: {trace.focus.source_id}")
            print(f"  创建: {trace.focus.created_at}")
            print(f"  访问次数: {trace.focus.access_count}")
            print(f"  演化事件: {[event['event_type'] for event in trace.evolution_events]}")
            continue
        if user_text == "/health":
            health = client.health()
            print(f"Bot: total={health.total_memories}, stale_ratio={health.stale_ratio:.2f}, suggestions={health.suggestions}")
            continue
        if user_text.startswith("/search "):
            query = user_text.split(maxsplit=1)[1]
            results = client.search(query, limit=5)
            for result in results:
                print(f"- {result.item.id}: {result.item.content} ({result.matched_by})")
            continue

        turns = [
            ConversationTurn(role="user", content=user_text, timestamp=datetime.now(timezone.utc)),
        ]
        created = client.ingest_conversation(turns, source_id=session_id)
        reply = generate_reply(client, user_text, provider=args.provider)
        if created:
            print(f"Bot: 已记住你的信息。{reply}")
        else:
            print(f"Bot: {reply}")


if __name__ == "__main__":
    raise SystemExit(main())
