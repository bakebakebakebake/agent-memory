from agent_memory import MemoryClient


client = MemoryClient()

client.add(
    "The user prefers SQLite for local-first agent systems.",
    source_id="example-session",
    tags=["preference", "database"],
)

for result in client.search("What database does the user prefer?"):
    print(result.item.content, result.score, result.matched_by)

