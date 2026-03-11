from __future__ import annotations

import pytest

from tests import model_connectivity_support as support


def test_load_cloud_request_config_forces_cloud_base_url():
    config = support.load_cloud_request_config()

    assert config["base_url"] == "https://api.cpagz.com"
    assert config["kb_name"] == "health clinic"
    assert config["request_template"]["stream"] is False
    assert config["request_template"]["model"] == "Qwen/Qwen3.5-397B-A17B"


def test_build_connectivity_cases_uses_all_mota_models_and_fixed_iflow_models():
    cases = support.build_connectivity_cases()

    mota_models = [model for provider_group, model in cases if provider_group == "mota"]
    iflow_models = [model for provider_group, model in cases if provider_group == "iflow"]

    assert "Qwen/Qwen3.5-397B-A17B" in mota_models
    assert "moonshotai/Kimi-K2.5" in mota_models
    assert "MiniMax/MiniMax-M2.5" in mota_models
    assert iflow_models == ["qwen3-max", "kimi-k2-0905"]
    assert len(mota_models) >= 9


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            {
                "status_code": 200,
                "response": {"choices": [{"message": {"content": "连接正常"}}]},
                "raw_text": '{"choices":[{"message":{"content":"连接正常"}}]}',
                "extracted_content": "连接正常",
            },
            None,
        ),
        (
            {
                "status_code": 200,
                "response": {"error": "provider failed"},
                "raw_text": '{"error":"provider failed"}',
                "extracted_content": "",
            },
            "provider failed",
        ),
        (
            {
                "status_code": 200,
                "response": {"raw": 'data: {"error":"upstream bad"}'},
                "raw_text": 'data: {"error":"upstream bad"}',
                "extracted_content": "",
            },
            "upstream bad",
        ),
        (
            {
                "status_code": 500,
                "response": {"detail": "bad gateway"},
                "raw_text": '{"detail":"bad gateway"}',
                "extracted_content": "",
            },
            "HTTP 500",
        ),
        (
            {
                "status_code": 200,
                "response": {"choices": [{"message": {"content": ""}}]},
                "raw_text": '{"choices":[{"message":{"content":""}}]}',
                "extracted_content": "",
            },
            "Empty content",
        ),
        (
            {
                "status_code": 200,
                "response": '{"id":"chat1","choices":[{"message":{"content":"您好，连接正常。我是小愈助手，随时为您服务。"}}]}',
                "raw_text": '"{\\"id\\":\\"chat1\\",\\"choices\\":[{\\"message\\":{\\"content\\":\\"您好，连接正常。我是小愈助手，随时为您服务。\\"}}]}"',
                "extracted_content": "您好，连接正常。我是小愈助手，随时为您服务。",
            },
            None,
        ),
    ],
)
def test_validate_connectivity_result_returns_actionable_error(result, expected):
    assert support.validate_connectivity_result(result) == expected


def test_extract_content_supports_json_string_wrapping_chat_completion():
    body = '{"id":"chat1","choices":[{"message":{"content":"您好，连接正常。我是小愈助手，随时为您服务。"}}]}'
    raw_text = '"{\\"id\\":\\"chat1\\",\\"choices\\":[{\\"message\\":{\\"content\\":\\"您好，连接正常。我是小愈助手，随时为您服务。\\"}}]}"'

    assert support._extract_content(body, raw_text) == "您好，连接正常。我是小愈助手，随时为您服务。"
