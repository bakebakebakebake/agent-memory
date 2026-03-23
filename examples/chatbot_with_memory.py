from agent_memory import ConversationTurn, MemoryClient


client = MemoryClient()

history = [
    ConversationTurn(role="user", content="我喜欢 SQLite，也想做一个有深度的 Agent 项目。"),
    ConversationTurn(role="assistant", content="好的，我会记住这些偏好。"),
]
client.ingest_conversation(history, source_id="chat-1")

question = "我更偏好什么数据库？"
results = client.search(question)

if results:
    print("Memory answer:", results[0].item.content)
else:
    print("No relevant memory yet.")

