from __future__ import annotations

import re


class EntityExtractor:
    def extract(self, text: str) -> list[str]:
        entities = set()
        entities.update(re.findall(r"#([\w-]+)", text))
        entities.update(re.findall(r"\b[A-Z][A-Za-z0-9_-]{1,}\b", text))
        entities.update(re.findall(r"[\u4e00-\u9fff]{2,8}", text))
        return sorted(entity.strip() for entity in entities if entity.strip())

