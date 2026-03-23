from agent_memory.models import ConversationTurn, MemoryType


def test_client_add_get_search_and_delete(client) -> None:
    item = client.add(
        "The user prefers SQLite for zero-config agent memory.",
        source_id="session-1",
        memory_type=MemoryType.SEMANTIC,
        tags=["preference"],
    )

    found = client.get(item.id)
    assert found is not None
    assert found.content == item.content

    results = client.search("What database does the user prefer?")
    assert results
    assert "SQLite" in results[0].item.content

    assert client.delete(item.id) is True
    assert client.search("SQLite") == []


def test_client_ingest_conversation(client) -> None:
    memories = client.ingest_conversation(
        [
            ConversationTurn(role="user", content="我喜欢 SQLite，正在做一个 Agent 记忆项目。"),
            ConversationTurn(role="assistant", content="收到。"),
        ],
        source_id="conversation-1",
    )
    assert memories
    assert any("SQLite" in memory.content for memory in memories)


def test_client_trace_graph_includes_descendants_and_history(client) -> None:
    root = client.add("User values traceability.", source_id="root")
    child = client.add("SQLite is chosen because traceability matters.", source_id="child", causal_parent_id=root.id)
    grandchild = client.add("WAL helps concurrent reads.", source_id="grandchild", causal_parent_id=child.id)

    report = client.trace_graph(root.id)
    assert report.focus.id == root.id
    assert [item.id for item in report.descendants] == [child.id, grandchild.id]
    assert report.evolution_events
