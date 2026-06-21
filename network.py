"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from dotenv import load_dotenv

from app_log import setup_logging
from models import Model, TempResult

load_dotenv()
logger = setup_logging()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_COMPATIBLE_TYPES = {"openai", "deepseek", "groq", "openrouter"}


class NetworkError(Exception):
    pass


def get_api_key(api_id: str) -> str:
    key = os.getenv(api_id, "").strip()
    if not key:
        raise NetworkError(f"Ключ «{api_id}» не найден в файле .env")
    return key


def _build_payload(
    model: Model,
    max_tokens: int,
    messages: list[dict[str, str]],
) -> dict:
    return {
        "model": model.name,
        "messages": messages,
        "max_tokens": max_tokens,
    }


def _build_headers(model: Model, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if model.model_type == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/chatlist"
        headers["X-OpenRouter-Title"] = "ChatList"
    return headers


def _extract_response(data: dict, model_type: str) -> str:
    if model_type in OPENROUTER_COMPATIBLE_TYPES:
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise NetworkError("Неожиданный формат ответа API") from exc
    raise NetworkError(f"Неподдерживаемый тип модели: {model_type}")


def send_chat(
    model: Model,
    messages: list[dict[str, str]],
    *,
    timeout: float = 30.0,
    max_tokens: int = 2048,
    log_tag: str = "CHAT",
) -> str:
    api_key = get_api_key(model.api_id)
    headers = _build_headers(model, api_key)
    payload = _build_payload(model, max_tokens, messages)
    preview = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            preview = str(message.get("content", ""))[:100].replace("\n", " ")
            break

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(model.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        logger.warning("%s FAIL | модель=%s | таймаут", log_tag, model.name)
        raise NetworkError(f"Таймаут запроса ({timeout} с)") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        logger.warning("%s FAIL | модель=%s | HTTP %s", log_tag, model.name, exc.response.status_code)
        raise NetworkError(f"HTTP {exc.response.status_code}: {detail}") from exc
    except httpx.RequestError as exc:
        logger.warning("%s FAIL | модель=%s | сеть: %s", log_tag, model.name, exc)
        raise NetworkError(f"Ошибка сети: {exc}") from exc

    result = _extract_response(data, model.model_type)
    logger.info(
        "%s OK | модель=%s | промт=%r | длина ответа=%d",
        log_tag,
        model.name,
        preview,
        len(result),
    )
    return result


def send_prompt(
    model: Model,
    prompt: str,
    *,
    timeout: float = 30.0,
    max_tokens: int = 2048,
) -> str:
    return send_chat(
        model,
        [{"role": "user", "content": prompt}],
        timeout=timeout,
        max_tokens=max_tokens,
        log_tag="REQUEST",
    )


def _send_one(
    model: Model,
    prompt: str,
    timeout: float,
    max_tokens: int,
) -> TempResult:
    preview = prompt[:100].replace("\n", " ")
    try:
        response = send_prompt(
            model,
            prompt,
            timeout=timeout,
            max_tokens=max_tokens,
        )
        logger.info(
            "Запрос OK | модель=%s | промт=%r | длина ответа=%d",
            model.name,
            preview,
            len(response),
        )
    except NetworkError as exc:
        response = str(exc)
        logger.warning(
            "Запрос FAIL | модель=%s | промт=%r | ошибка=%s",
            model.name,
            preview,
            exc,
        )
    except Exception as exc:
        response = f"Ошибка: {exc}"
        logger.exception(
            "Запрос ERROR | модель=%s | промт=%r",
            model.name,
            preview,
        )
    return TempResult(
        model_id=model.id,
        model_name=model.name,
        response=response,
        selected=False,
    )


def send_to_all_models(
    models: list[Model],
    prompt: str,
    *,
    timeout: float = 30.0,
    max_tokens: int = 2048,
) -> list[TempResult]:
    if not models:
        return []

    results: list[TempResult] = []
    with ThreadPoolExecutor(max_workers=min(len(models), 8)) as executor:
        futures = {
            executor.submit(_send_one, model, prompt, timeout, max_tokens): model
            for model in models
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item.model_name.lower())
    return results


def fetch_openrouter_models(
    api_id: str = OPENROUTER_API_KEY_ENV,
    *,
    timeout: float = 30.0,
) -> list[dict[str, str]]:
    """Загружает каталог моделей OpenRouter (https://openrouter.ai/docs)."""
    headers: dict[str, str] = {}
    try:
        api_key = get_api_key(api_id)
        headers["Authorization"] = f"Bearer {api_key}"
    except NetworkError:
        pass

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(OPENROUTER_MODELS_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise NetworkError(f"Таймаут загрузки каталога OpenRouter ({timeout} с)") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        raise NetworkError(f"HTTP {exc.response.status_code}: {detail}") from exc
    except httpx.RequestError as exc:
        raise NetworkError(f"Ошибка сети: {exc}") from exc

    models: list[dict[str, str]] = []
    for item in data.get("data", []):
        model_id = str(item.get("id", "")).strip()
        if not model_id:
            continue
        models.append(
            {
                "id": model_id,
                "name": str(item.get("name") or model_id).strip(),
                "description": str(item.get("description") or "").strip(),
            },
        )
    models.sort(key=lambda item: item["id"].lower())
    return models
