from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import yaml

from tests.chat_response_parsing import extract_content_from_payload, extract_error_from_payload


CLOUD_BASE_URL = "https://api.cpagz.com"
DEFAULT_PROMPT = '你好，请简单回复“连接正常”'
IFLOW_MODELS = ["qwen3-max", "kimi-k2-0905"]


def build_messages(user_text: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": user_text}]


def load_cloud_request_config() -> dict[str, Any]:
    config_path = Path(__file__).parent / "kb_chat_request.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return {
        "base_url": CLOUD_BASE_URL,
        "kb_name": config["kb_name"],
        "request_template": dict(config["request"]),
    }


def load_platform_models(platform_name: str) -> list[str]:
    config_path = Path(__file__).parent.parent / "data1" / "model_settings.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    for platform in config.get("MODEL_PLATFORMS", []):
        if platform.get("platform_name") == platform_name:
            return list(platform.get("llm_models", []))

    raise KeyError(f"Platform not found in model_settings.yaml: {platform_name}")


def build_connectivity_cases() -> list[tuple[str, str]]:
    cases = [("mota", model) for model in load_platform_models("mota")]
    cases.extend(("iflow", model) for model in IFLOW_MODELS)
    return cases


def _extract_content(body: Any, raw_text: str) -> str:
    if isinstance(raw_text, str) and "data:" in raw_text:
        chunks: list[str] = []
        for line in raw_text.splitlines():
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if not data or data == "[DONE]":
                break
            piece = extract_content_from_payload(data)
            if piece:
                chunks.append(piece)

        if chunks:
            return "".join(chunks).strip()

    return extract_content_from_payload(body)


def extract_response_error(response: Any, raw_text: str) -> str | None:
    error = extract_error_from_payload(response)
    if error:
        return error
    return extract_error_from_payload(raw_text)


def call_cloud_chat_api(model: str, question: str = DEFAULT_PROMPT) -> dict[str, Any]:
    config = load_cloud_request_config()
    request_template = dict(config["request_template"])
    request_template["stream"] = False
    request_template["model"] = model
    endpoint = f"{config['base_url']}/knowledge_base/local_kb/{quote(config['kb_name'])}/chat/completions"
    payload = {**request_template, "messages": build_messages(question)}

    response = httpx.post(endpoint, json=payload, timeout=90)
    raw_text = response.text
    try:
        body = response.json()
    except Exception:
        body = {"raw": raw_text}

    return {
        "status_code": response.status_code,
        "response": body,
        "raw_text": raw_text,
        "extracted_content": _extract_content(body, raw_text),
        "error_message": extract_response_error(body, raw_text),
    }


def validate_connectivity_result(result: dict[str, Any]) -> str | None:
    status_code = result.get("status_code")
    if status_code != 200:
        return f"HTTP {status_code}"

    error_message = result.get("error_message")
    if not error_message:
        error_message = extract_response_error(result.get("response"), str(result.get("raw_text", "")))
    if isinstance(error_message, str) and error_message.strip():
        return error_message.strip()

    content = result.get("extracted_content")
    if not isinstance(content, str) or not content.strip():
        return "Empty content"

    return None
