from pathlib import Path
from urllib.parse import quote

import httpx
import yaml


def build_messages(user_text: str, history: list | None = None) -> list:
    history = history or []
    return history + [{"role": "user", "content": user_text}]


def load_request_config() -> dict:
    config_path = Path(__file__).parent / "kb_chat_request.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_kb_chat_backend_connection():
    config = load_request_config()
    base_url = config["base_url"]
    kb_name = config["kb_name"]
    request_config = config["request"]

    endpoint = f"{base_url}/knowledge_base/local_kb/{quote(kb_name)}/chat/completions"

    payload = {
        **request_config,
        "messages": build_messages("你好,我头痛,有什么方法"),
    }

    response = httpx.post(endpoint, json=payload, timeout=60)

    print("Status:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception:
        print("Response Text:", response.text)

    assert response.status_code == 200
