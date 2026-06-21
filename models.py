"""Бизнес-логика: промты, модели и временные результаты."""

from __future__ import annotations

from dataclasses import dataclass

import db


@dataclass
class Prompt:
    id: int
    created_at: str
    text: str
    tags: str = ""


@dataclass
class Model:
    id: int
    name: str
    api_url: str
    api_id: str
    is_active: bool
    model_type: str = "openai"


@dataclass
class Result:
    id: int
    prompt_id: int
    model_id: int
    response: str
    created_at: str


@dataclass
class HistoryResult:
    id: int
    prompt_id: int
    model_id: int
    response: str
    created_at: str
    prompt_text: str
    model_name: str


def _history_result_from_row(row: dict) -> HistoryResult:
    return HistoryResult(
        id=int(row["id"]),
        prompt_id=int(row["prompt_id"]),
        model_id=int(row["model_id"]),
        response=str(row["response"]),
        created_at=str(row["created_at"]),
        prompt_text=str(row["prompt_text"]),
        model_name=str(row["model_name"]),
    )


@dataclass
class TempResult:
    model_id: int
    model_name: str
    response: str
    selected: bool = False


def _prompt_from_row(row: dict) -> Prompt:
    return Prompt(
        id=int(row["id"]),
        created_at=str(row["created_at"]),
        text=str(row["text"]),
        tags=str(row.get("tags") or ""),
    )


def _model_from_row(row: dict) -> Model:
    return Model(
        id=int(row["id"]),
        name=str(row["name"]),
        api_url=str(row["api_url"]),
        api_id=str(row["api_id"]),
        is_active=bool(row["is_active"]),
        model_type=str(row.get("model_type") or "openai"),
    )


def _result_from_row(row: dict) -> Result:
    return Result(
        id=int(row["id"]),
        prompt_id=int(row["prompt_id"]),
        model_id=int(row["model_id"]),
        response=str(row["response"]),
        created_at=str(row["created_at"]),
    )


class ChatService:
    def __init__(self) -> None:
        db.init_db()
        self.temp_results: list[TempResult] = []
        self.current_prompt_id: int | None = None
        self.current_prompt_text: str = ""

    def load_prompts(self, search: str = "") -> list[Prompt]:
        rows = db.get_prompts(search or None)
        return [_prompt_from_row(row) for row in rows]

    def get_prompt(self, prompt_id: int) -> Prompt | None:
        row = db.get_prompt_by_id(prompt_id)
        return _prompt_from_row(row) if row else None

    def select_saved_prompt(self, prompt_id: int) -> Prompt | None:
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return None
        self.current_prompt_id = prompt.id
        self.current_prompt_text = prompt.text
        return prompt

    def resolve_prompt_id(self, text: str) -> int:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Промт не может быть пустым")
        if (
            self.current_prompt_id is not None
            and normalized == self.current_prompt_text.strip()
        ):
            return self.current_prompt_id
        prompt_id = db.create_prompt(normalized)
        self.current_prompt_id = prompt_id
        self.current_prompt_text = normalized
        return prompt_id

    def load_active_models(self) -> list[Model]:
        rows = db.get_active_models()
        return [_model_from_row(row) for row in rows]

    def load_all_models(self) -> list[Model]:
        rows = db.get_all_models()
        return [_model_from_row(row) for row in rows]

    def clear_temp_results(self) -> None:
        self.temp_results.clear()

    def set_temp_results(self, results: list[TempResult]) -> None:
        self.temp_results = list(results)

    def add_temp_result(self, result: TempResult) -> None:
        self.temp_results.append(result)

    def get_selected_results(self) -> list[TempResult]:
        return [item for item in self.temp_results if item.selected]

    def set_selected(self, index: int, selected: bool) -> None:
        if 0 <= index < len(self.temp_results):
            self.temp_results[index].selected = selected

    def save_selected_results(self) -> int:
        if self.current_prompt_id is None:
            raise ValueError("Нет активного промта для сохранения")
        selected = self.get_selected_results()
        if not selected:
            return 0
        saved = db.save_results(
            self.current_prompt_id,
            [(item.model_id, item.response) for item in selected],
        )
        self.clear_temp_results()
        return saved

    def get_request_timeout(self) -> float:
        value = db.get_setting("request_timeout", "30")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 30.0

    def get_max_tokens(self) -> int:
        value = db.get_setting("max_tokens", "2048")
        try:
            return int(value)
        except (TypeError, ValueError):
            return 2048

    def get_saved_results(self, prompt_id: int | None = None) -> list[Result]:
        rows = db.get_results(prompt_id)
        return [_result_from_row(row) for row in rows]

    def get_model(self, model_id: int) -> Model | None:
        row = db.get_model_by_id(model_id)
        return _model_from_row(row) if row else None

    def create_model(
        self,
        name: str,
        api_url: str,
        api_id: str,
        *,
        is_active: bool = True,
        model_type: str = "openai",
    ) -> int:
        return db.create_model(name, api_url, api_id, is_active, model_type)

    def update_model(self, model_id: int, **kwargs) -> None:
        db.update_model(model_id, **kwargs)

    def delete_model(self, model_id: int) -> None:
        db.delete_model(model_id)

    def toggle_model_active(self, model_id: int) -> None:
        model = self.get_model(model_id)
        if model is None:
            raise ValueError("Модель не найдена")
        db.update_model(model_id, is_active=not model.is_active)

    def get_settings(self) -> dict[str, str]:
        return db.get_all_settings()

    def save_settings(self, settings: dict[str, str]) -> None:
        for key, value in settings.items():
            db.set_setting(key, value.strip())

    def load_history_results(
        self,
        prompt_id: int | None = None,
        search: str = "",
    ) -> list[HistoryResult]:
        rows = db.get_results_detailed(prompt_id, search or None)
        return [_history_result_from_row(row) for row in rows]

    def delete_prompt(self, prompt_id: int) -> None:
        db.delete_prompt(prompt_id)
        if self.current_prompt_id == prompt_id:
            self.current_prompt_id = None
            self.current_prompt_text = ""

    def is_assistant_enabled(self) -> bool:
        return db.get_setting("assistant_enabled", "1") == "1"

    def get_assistant_system_prompt(self) -> str | None:
        custom = (db.get_setting("assistant_system_prompt") or "").strip()
        return custom or None

    def get_assistant_model(self) -> Model | None:
        if not self.is_assistant_enabled():
            return None
        model_id_raw = (db.get_setting("assistant_model_id") or "").strip()
        if not model_id_raw:
            return None
        try:
            model_id = int(model_id_raw)
        except ValueError:
            return None
        return self.get_model(model_id)

    def improve_current_prompt(self, text: str):
        from prompt_assistant import improve_prompt

        model = self.get_assistant_model()
        if model is None:
            raise ValueError(
                "Модель ассистента не настроена. Откройте «Приложение → Настройки».",
            )
        return improve_prompt(
            text,
            model,
            timeout=self.get_request_timeout(),
            max_tokens=self.get_max_tokens(),
            system_prompt=self.get_assistant_system_prompt(),
        )
