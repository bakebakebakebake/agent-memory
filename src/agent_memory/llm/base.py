from __future__ import annotations

from typing import Any
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        ...

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        ...


class LLMClientError(RuntimeError):
    pass
