from agent_memory.extraction.entity_extractor import EntityExtractor
from agent_memory.extraction.pipeline import ConversationMemoryPipeline
from agent_memory.models import ConversationTurn


class FakeLLMClient:
    def generate_json(self, *, prompt, schema, schema_name, system_prompt=None):
        return {
            "memories": [
                {
                    "content": "The user prefers SQLite for local-first agent systems.",
                    "memory_type": "semantic",
                    "importance": 0.9,
                    "trust_score": 0.85,
                    "tags": ["preference", "llm"],
                }
            ]
        }


def test_entity_extractor_collects_basic_entities() -> None:
    extractor = EntityExtractor()
    entities = extractor.extract("我喜欢 SQLite 和 Python #memory")
    assert "SQLite" in entities
    assert "Python" in entities
    assert "memory" in entities


def test_pipeline_extracts_user_preferences() -> None:
    pipeline = ConversationMemoryPipeline()
    turns = [
        ConversationTurn(role="user", content="我喜欢 SQLite，也在做 Agent 记忆系统。"),
        ConversationTurn(role="assistant", content="好的，我记住了。"),
    ]
    drafts = pipeline.extract(turns, source_id="conv-1")
    assert len(drafts) >= 1
    assert any("SQLite" in draft.content for draft in drafts)


def test_pipeline_prefers_llm_structured_extraction_when_available() -> None:
    pipeline = ConversationMemoryPipeline(llm_client=FakeLLMClient())
    turns = [
        ConversationTurn(role="user", content="I prefer SQLite because it is easy to demo."),
        ConversationTurn(role="assistant", content="Noted."),
    ]
    drafts = pipeline.extract(turns, source_id="conv-llm")
    assert len(drafts) == 1
    assert drafts[0].tags == ["preference", "llm"]
