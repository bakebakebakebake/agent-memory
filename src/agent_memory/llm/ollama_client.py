from __future__ import annotations

import json
import os
from typing import Any
from urllib import request

from agent_memory.llm.base import LLMClientError


class OllamaClient:
    def __init__(self, model: str = "llama3.1", base_url: str | None = None) -> None:
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        response = self._request_json("/api/generate", payload)
        if "response" not in response:
            raise LLMClientError(f"Ollama response missing text: {response}")
        return str(response["response"])

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
        }
        if system_prompt:
            payload["system"] = system_prompt
        response = self._request_json("/api/generate", payload)
        text = str(response.get("response", "")).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Ollama response was not valid JSON: {text}") from exc

    def _request_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise LLMClientError(f"Ollama request failed: {exc}") from exc
