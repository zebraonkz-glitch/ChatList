"""Тесты сценариев ChatList (этап 8 PLAN.md)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import db
import export_utils
import network
from models import ChatService, TempResult, _model_from_row


class ChatListTestCase(unittest.TestCase):
    def setUp(self) -> None:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._db_path = Path(handle.name)
        handle.close()
        self._original_db_path = db.DEFAULT_DB_PATH
        db.DEFAULT_DB_PATH = self._db_path
        db.init_db()

    def tearDown(self) -> None:
        db.DEFAULT_DB_PATH = self._original_db_path
        if self._db_path.exists():
            self._db_path.unlink()

    def _create_active_model(self, name: str = "test-model") -> int:
        return db.create_model(
            name,
            "https://example.com/v1/chat/completions",
            "TEST_API_KEY",
            is_active=True,
            model_type="openai",
        )


class TestPromptSendSelectSave(ChatListTestCase):
    """Сценарий: ввод промта → ответы → выбор → сохранение."""

    def test_full_workflow(self) -> None:
        model_id = self._create_active_model()
        service = ChatService()

        prompt_id = service.resolve_prompt_id("Что такое Python?")
        self.assertEqual(prompt_id, service.current_prompt_id)

        service.set_temp_results(
            [
                TempResult(model_id, "test-model", "Python — язык программирования.", False),
                TempResult(model_id, "test-model-2", "Другой ответ.", False),
            ],
        )
        service.set_selected(0, True)
        self.assertEqual(len(service.get_selected_results()), 1)

        saved = service.save_selected_results()
        self.assertEqual(saved, 1)
        self.assertEqual(len(service.temp_results), 0)

        stored = service.get_saved_results(prompt_id)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].response, "Python — язык программирования.")


class TestSavedPromptResend(ChatListTestCase):
    """Сценарий: выбор сохранённого промта → повторная отправка."""

    def test_reuse_saved_prompt_id(self) -> None:
        service = ChatService()
        created_id = db.create_prompt("Объясни asyncio")

        prompt = service.select_saved_prompt(created_id)
        self.assertIsNotNone(prompt)
        self.assertEqual(service.current_prompt_id, created_id)

        same_id = service.resolve_prompt_id("Объясни asyncio")
        self.assertEqual(same_id, created_id)

        prompts_before = len(service.load_prompts())
        service.resolve_prompt_id("Объясни asyncio ")
        self.assertEqual(len(service.load_prompts()), prompts_before)

        new_id = service.resolve_prompt_id("Новый другой промт")
        self.assertNotEqual(new_id, created_id)
        self.assertEqual(len(service.load_prompts()), prompts_before + 1)


class TestNetworkErrors(ChatListTestCase):
    """Сценарий: ошибки API и отсутствие ключей в .env."""

    def test_missing_env_key_raises(self) -> None:
        with self.assertRaises(network.NetworkError) as ctx:
            network.get_api_key("ABSENT_KEY_FOR_TEST")
        self.assertIn(".env", str(ctx.exception))

    def test_send_one_without_key_returns_error_text(self) -> None:
        model_id = self._create_active_model()
        row = db.get_model_by_id(model_id)
        assert row is not None
        model = _model_from_row(row)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_API_KEY", None)
            result = network._send_one(model, "Привет", timeout=5.0, max_tokens=100)

        self.assertIn("не найден", result.response.lower())

    @patch("network.httpx.Client")
    def test_http_error_returns_message(self, client_cls: MagicMock) -> None:
        model_id = self._create_active_model()
        model = _model_from_row(db.get_model_by_id(model_id))

        response = MagicMock()
        response.status_code = 401
        response.text = "Unauthorized"
        response.raise_for_status.side_effect = network.httpx.HTTPStatusError(
            "401",
            request=MagicMock(),
            response=response,
        )
        client_cls.return_value.__enter__.return_value.post.return_value = response

        with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}):
            result = network._send_one(model, "Привет", timeout=5.0, max_tokens=100)

        self.assertIn("401", result.response)


class TestExport(ChatListTestCase):
    def test_export_formats(self) -> None:
        items = [TempResult(1, "gpt-4o", "Ответ модели", True)]
        md = export_utils.export_markdown("Тестовый промт", items)
        self.assertIn("# ChatList", md)
        self.assertIn("gpt-4o", md)
        self.assertIn("Тестовый промт", md)

        js = export_utils.export_json("Тестовый промт", items, prompt_id=5)
        self.assertIn('"prompt_id": 5', js)
        self.assertIn('"model_name": "gpt-4o"', js)


if __name__ == "__main__":
    unittest.main()
