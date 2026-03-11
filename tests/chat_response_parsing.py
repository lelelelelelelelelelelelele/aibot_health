from __future__ import annotations

import json
import re
from typing import Any


CONTENT_FIELD_PATTERN = re.compile(r'"content"\s*:\s*"((?:\\.|[^"\\])*)"')
DOCS_FIELD_PATTERN = re.compile(r'"docs"\s*:')


def normalize_json_payload(value: Any) -> Any:
    current = value
    for _ in range(3):
        if not isinstance(current, str):
            return current
        stripped = current.strip()
        if not stripped:
            return current
        try:
            parsed = json.loads(stripped)
        except Exception:
            return current
        if parsed == current:
            return current
        current = parsed
    return current


def _decode_escaped_content(raw_value: str) -> str:
    try:
        return json.loads(f'"{raw_value}"')
    except Exception:
        return ""


def extract_content_from_parsed_payload(parsed: Any) -> str:
    if not isinstance(parsed, dict):
        return ""

    choices = parsed.get("choices")
    if not (isinstance(choices, list) and choices and isinstance(choices[0], dict)):
        return ""

    choice = choices[0]
    delta_content = choice.get("delta", {}).get("content") if isinstance(choice.get("delta"), dict) else None
    if isinstance(delta_content, str):
        return delta_content

    message_content = choice.get("message", {}).get("content") if isinstance(choice.get("message"), dict) else None
    if isinstance(message_content, str):
        return message_content

    text_content = choice.get("text")
    if isinstance(text_content, str):
        return text_content

    return ""


def extract_docs_from_parsed_payload(parsed: Any) -> bool:
    if not isinstance(parsed, dict):
        return False
    docs = parsed.get("docs")
    if isinstance(docs, list):
        return len(docs) > 0
    return bool(docs)


def extract_content_from_payload(payload: Any) -> str:
    normalized = normalize_json_payload(payload)

    if isinstance(normalized, dict):
        return extract_content_from_parsed_payload(normalized)

    if not isinstance(normalized, str):
        return ""

    matches = CONTENT_FIELD_PATTERN.findall(normalized)
    if not matches:
        return ""

    return "".join(_decode_escaped_content(match) for match in matches if match).strip()


def extract_docs_from_payload(payload: Any) -> bool:
    normalized = normalize_json_payload(payload)

    if isinstance(normalized, dict):
        return extract_docs_from_parsed_payload(normalized)

    if not isinstance(normalized, str):
        return False

    return bool(DOCS_FIELD_PATTERN.search(normalized))


def extract_error_from_payload(payload: Any) -> str | None:
    normalized = normalize_json_payload(payload)

    if isinstance(normalized, dict):
        error = normalized.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        data_value = normalized.get("data")
        if data_value is not None:
            return extract_error_from_payload(data_value)

    if not isinstance(normalized, str):
        return None

    for line in normalized.splitlines():
        data = line.strip()
        if data.startswith("data:"):
            data = data[len("data:") :].strip()
        if not data:
            continue
        nested = normalize_json_payload(data)
        if isinstance(nested, dict):
            error = nested.get("error")
            if isinstance(error, str) and error.strip():
                return error.strip()
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()

    return None
