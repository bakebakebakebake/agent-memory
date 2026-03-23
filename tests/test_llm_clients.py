import json

from agent_memory.llm.ollama_client import OllamaClient
from agent_memory.llm.openai_client import OpenAIClient


def test_openai_client_generate_json_payload_and_parse(monkeypatch) -> None:
    captured = {}

    def fake_request(self, path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"memories": []}),
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(OpenAIClient, "_request_json", fake_request)
    client = OpenAIClient(api_key="test-key")
    response = client.generate_json(
        prompt="extract",
        schema={"type": "object", "properties": {"memories": {"type": "array"}}, "required": ["memories"]},
        schema_name="memory_extraction",
    )
    assert captured["path"] == "/responses"
    assert captured["payload"]["text"]["format"]["type"] == "json_schema"
    assert response == {"memories": []}


def test_ollama_client_generate_json_payload_and_parse(monkeypatch) -> None:
    captured = {}

    def fake_request(self, path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"response": json.dumps({"content": "merged"})}

    monkeypatch.setattr(OllamaClient, "_request_json", fake_request)
    client = OllamaClient()
    response = client.generate_json(
        prompt="merge",
        schema={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        schema_name="consolidation",
    )
    assert captured["path"] == "/api/generate"
    assert captured["payload"]["format"]["type"] == "object"
    assert response == {"content": "merged"}
