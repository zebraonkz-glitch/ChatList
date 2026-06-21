"""Экспорт выбранных результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import datetime

from models import TempResult


def export_markdown(prompt_text: str, items: list[TempResult]) -> str:
    lines = [
        "# ChatList — экспорт",
        "",
        f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Промт",
        "",
        prompt_text.strip(),
        "",
        "## Ответы",
        "",
    ]
    for index, item in enumerate(items, 1):
        lines.extend(
            [
                f"### {index}. {item.model_name}",
                "",
                item.response.strip(),
                "",
            ],
        )
    return "\n".join(lines)


def export_json(
    prompt_text: str,
    items: list[TempResult],
    *,
    prompt_id: int | None = None,
) -> str:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "prompt_id": prompt_id,
        "prompt": prompt_text.strip(),
        "results": [
            {
                "model_id": item.model_id,
                "model_name": item.model_name,
                "response": item.response,
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
