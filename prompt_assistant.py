"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import network
from models import Model

DEFAULT_SYSTEM_PROMPT = """Ты — ассистент по улучшению промтов для нейросетей.
Пользователь пришлёт исходный промт. Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{
  "improved": "улучшенная версия промта",
  "alternatives": ["вариант 1", "вариант 2", "вариант 3"],
  "adaptations": {
    "code": "адаптация для задач программирования",
    "analysis": "адаптация для анализа и исследований",
    "creative": "адаптация для креативных задач"
  }
}
alternatives — ровно 2–3 переформулировки. adaptations — три ключа: code, analysis, creative.
Отвечай на том же языке, что и исходный промт."""


@dataclass
class PromptSuggestion:
    original: str
    improved: str
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "improved": self.improved,
            "alternatives": self.alternatives,
            "adaptations": self.adaptations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PromptSuggestion:
        return cls(
            original=str(data.get("original", "")),
            improved=str(data.get("improved", "")),
            alternatives=[str(x) for x in data.get("alternatives", [])],
            adaptations={str(k): str(v) for k, v in (data.get("adaptations") or {}).items()},
        )


def build_assistant_messages(
    user_prompt: str,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    system = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt.strip()},
    ]


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def parse_assistant_response(original: str, raw: str) -> PromptSuggestion:
    try:
        data = json.loads(_extract_json_text(raw))
        alternatives = [str(x).strip() for x in data.get("alternatives", []) if str(x).strip()][:3]
        adaptations_raw = data.get("adaptations") or {}
        adaptations = {
            str(key): str(value).strip()
            for key, value in adaptations_raw.items()
            if str(value).strip()
        }
        improved = str(data.get("improved", "")).strip() or raw.strip()
        return PromptSuggestion(
            original=original,
            improved=improved,
            alternatives=alternatives,
            adaptations=adaptations,
        )
    except (json.JSONDecodeError, TypeError, AttributeError):
        return PromptSuggestion(original=original, improved=raw.strip())


def improve_prompt(
    prompt: str,
    model: Model,
    *,
    timeout: float = 30.0,
    max_tokens: int = 2048,
    system_prompt: str | None = None,
) -> PromptSuggestion:
    normalized = prompt.strip()
    if not normalized:
        raise ValueError("Промт не может быть пустым")

    messages = build_assistant_messages(normalized, system_prompt)
    raw = network.send_chat(
        model,
        messages,
        timeout=timeout,
        max_tokens=max_tokens,
        log_tag="ASSISTANT",
    )
    return parse_assistant_response(normalized, raw)
