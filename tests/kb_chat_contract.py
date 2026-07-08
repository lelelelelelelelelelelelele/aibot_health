from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml


RAG_EXTRA_BODY_KEYS = {
    "top_k",
    "score_threshold",
    "temperature",
    "prompt_name",
    "return_direct",
}


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUEST_CONFIG_PATH = Path(__file__).parent / "kb_chat_request.yaml"


def build_messages(user_text: str, history: list | None = None) -> list[dict[str, str]]:
    history = history or []
    return history + [{"role": "user", "content": user_text}]


def load_request_config() -> dict[str, Any]:
    with REQUEST_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_kb_chat_endpoint(config: dict[str, Any] | None = None) -> str:
    config = config or load_request_config()
    base_url = config["base_url"]
    kb_name = config["kb_name"]
    return f"{base_url}/knowledge_base/local_kb/{quote(kb_name)}/chat/completions"


def build_kb_chat_payload(
    question: str,
    history: list | None = None,
    stream: bool | None = None,
    extra_body_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_request_config()
    request_config = dict(config["request"])
    extra_body = dict(request_config.get("extra_body") or {})
    if extra_body_overrides:
        extra_body.update(extra_body_overrides)

    top_level_rag_keys = RAG_EXTRA_BODY_KEYS.intersection(request_config)
    if top_level_rag_keys:
        raise ValueError(f"RAG keys must live under extra_body, found top-level keys: {sorted(top_level_rag_keys)}")
    missing_extra_body_keys = RAG_EXTRA_BODY_KEYS.difference(extra_body)
    if missing_extra_body_keys:
        raise ValueError(f"extra_body is missing required RAG keys: {sorted(missing_extra_body_keys)}")

    return {
        "model": request_config["model"],
        "stream": request_config.get("stream", False) if stream is None else stream,
        "messages": build_messages(question, history),
        "extra_body": extra_body,
    }
