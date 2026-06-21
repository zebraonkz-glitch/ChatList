"""Тесты AI-ассистента промтов (этап 9 PLAN.md)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import network
from models import Model
from prompt_assistant import (
    DEFAULT_SYSTEM_PROMPT,
    PromptSuggestion,
    build_assistant_messages,
    improve_prompt,
    parse_assistant_response,
)


def _sample_model() -> Model:
    return Model(
        id=1,
        name="openai/gpt-4o-mini",
        api_url="https://openrouter.ai/api/v1/chat/completions",
        api_id="OPENROUTER_API_KEY",
        model_type="openrouter",
        is_active=True,
    )


class PromptAssistantTestCase(unittest.TestCase):
    def test_build_assistant_messages_default_system(self) -> None:
        messages = build_assistant_messages("Привет")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], DEFAULT_SYSTEM_PROMPT)
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Привет")

    def test_build_assistant_messages_custom_system(self) -> None:
        messages = build_assistant_messages("Test", system_prompt="Custom prompt")
        self.assertEqual(messages[0]["content"], "Custom prompt")

    def test_parse_valid_json(self) -> None:
        raw = """
        {
          "improved": "Улучшенный промт",
          "alternatives": ["Альт 1", "Альт 2"],
          "adaptations": {"code": "Для кода", "analysis": "Для анализа"}
        }
        """
        suggestion = parse_assistant_response("Исходный", raw)
        self.assertEqual(suggestion.original, "Исходный")
        self.assertEqual(suggestion.improved, "Улучшенный промт")
        self.assertEqual(suggestion.alternatives, ["Альт 1", "Альт 2"])
        self.assertEqual(suggestion.adaptations["code"], "Для кода")

    def test_parse_json_in_markdown_fence(self) -> None:
        raw = '```json\n{"improved": "OK", "alternatives": [], "adaptations": {}}\n```'
        suggestion = parse_assistant_response("x", raw)
        self.assertEqual(suggestion.improved, "OK")

    def test_parse_invalid_json_fallback(self) -> None:
        raw = "Просто текст без JSON"
        suggestion = parse_assistant_response("Исходный", raw)
        self.assertEqual(suggestion.improved, "Просто текст без JSON")
        self.assertEqual(suggestion.alternatives, [])

    def test_parse_empty_json_fallback(self) -> None:
        suggestion = parse_assistant_response("Исходный", "{}")
        self.assertEqual(suggestion.improved, "{}")

    def test_improve_prompt_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            improve_prompt("   ", _sample_model())

    @patch("prompt_assistant.network.send_chat")
    def test_improve_prompt_api_error(self, send_chat_mock) -> None:
        send_chat_mock.side_effect = network.NetworkError("HTTP 500")
        with self.assertRaises(network.NetworkError):
            improve_prompt("Тест", _sample_model())

    @patch("prompt_assistant.network.send_chat")
    def test_improve_prompt_success(self, send_chat_mock) -> None:
        send_chat_mock.return_value = (
            '{"improved": "Better", "alternatives": ["A"], "adaptations": {}}'
        )
        suggestion = improve_prompt("Test", _sample_model())
        self.assertIsInstance(suggestion, PromptSuggestion)
        self.assertEqual(suggestion.improved, "Better")
        send_chat_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
