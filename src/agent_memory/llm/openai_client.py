from __future__ import annotations

import json
import os
from typing import Any
from urllib import request

from agent_memory.llm.base import LLMClientError


class OpenAIClient:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "input": self._build_input(prompt=prompt, system_prompt=system_prompt),
        }
        response = self._request_json("/responses", payload)
        return self._extract_output_text(response)

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "input": self._build_input(prompt=prompt, system_prompt=system_prompt),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        response = self._request_json("/responses", payload)
        text = self._extract_output_text(response)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"OpenAI response was not valid JSON: {text}") from exc

    def _build_input(self, *, prompt: str, system_prompt: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _request_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise LLMClientError("OPENAI_API_KEY is required to use OpenAIClient.")
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise LLMClientError(f"OpenAI request failed: {exc}") from exc

    def _extract_output_text(self, response: dict[str, Any]) -> str:
        for output in response.get("output", []):
            if output.get("type") != "message":
                continue
            for item in output.get("content", []):
                if item.get("type") == "refusal":
                    raise LLMClientError(item.get("refusal", "Model refused request."))
                if item.get("type") in {"output_text", "text"} and item.get("text"):
                    return str(item["text"])
        if response.get("output_text"):
            return str(response["output_text"])
        raise LLMClientError(f"Could not extract text from OpenAI response: {response}")
