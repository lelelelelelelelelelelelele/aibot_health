from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import pytest
import yaml


def build_messages(user_text: str, history: list | None = None) -> list[dict[str, str]]:
    history = history or []
    return history + [{"role": "user", "content": user_text}]


def load_request_config() -> dict[str, Any]:
    config_path = Path(__file__).parent / "kb_chat_request.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def call_kb_chat_api(question: str, history: list | None = None, stream: bool = False) -> dict[str, Any]:
    config = load_request_config()
    base_url = config["base_url"]
    kb_name = config["kb_name"]
    request_config = dict(config["request"])  # shallow copy
    request_config["stream"] = stream

    endpoint = f"{base_url}/knowledge_base/local_kb/{quote(kb_name)}/chat/completions"

    payload = {**request_config, "messages": build_messages(question, history)}

    response = httpx.post(endpoint, json=payload, timeout=60)
    raw_text = response.text
    try:
        body = response.json()
    except Exception:
        body = {"raw": raw_text}

    content = _extract_content(body, raw_text)

    return {
        "status_code": response.status_code,
        "response": body,
        "extracted_content": content,
        "raw_text": raw_text,
    }


def _extract_content(body: Any, raw_text: str) -> str:
    """Best-effort extract assistant text from OpenAI-compatible responses.

    Supports both non-stream JSON and SSE-style streaming bodies ("data: {...}").
    """
    # 1) SSE streaming format in raw text
    if isinstance(raw_text, str) and "data:" in raw_text:
        chunks: list[str] = []
        for line in raw_text.splitlines():
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if not data or data == "[DONE]":
                break
            try:
                evt = json.loads(data)
            except Exception:
                continue

            if not isinstance(evt, dict):
                continue
            choices = evt.get("choices")
            if not (isinstance(choices, list) and choices):
                continue
            c0 = choices[0] if isinstance(choices[0], dict) else {}
            delta = c0.get("delta")
            if isinstance(delta, dict):
                piece = delta.get("content")
                if isinstance(piece, str) and piece:
                    chunks.append(piece)
            msg = c0.get("message")
            if isinstance(msg, dict):
                piece = msg.get("content")
                if isinstance(piece, str) and piece:
                    chunks.append(piece)
            piece = c0.get("text")
            if isinstance(piece, str) and piece:
                chunks.append(piece)

        if chunks:
            return "".join(chunks).strip()

    # 2) Non-stream JSON shapes
    if isinstance(body, dict):
        choices = body.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            c0 = choices[0]
            msg = c0.get("message")
            if isinstance(msg, dict):
                piece = msg.get("content")
                if isinstance(piece, str) and piece:
                    return piece.strip()
            delta = c0.get("delta")
            if isinstance(delta, dict):
                piece = delta.get("content")
                if isinstance(piece, str) and piece:
                    return piece.strip()
            piece = c0.get("text")
            if isinstance(piece, str) and piece:
                return piece.strip()

    return ""


def _call_or_skip(question: str, history: list | None = None) -> dict:
    """调用后端；若后端未启动/不可达则跳过测试。"""
    try:
        return call_kb_chat_api(question, history=history, stream=False)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        pytest.skip(f"KB chat backend not reachable: {e!r}")


def _missing_elements(answer: str, expected_elements: list[str]) -> list[str]:
    lower = answer.lower()
    return [e for e in expected_elements if e.lower() not in lower]


def _run_case(
    *,
    kb_chat_results: list[dict[str, Any]],
    test_name: str,
    question: str,
    expected_elements: list[str],
    history: list[dict[str, str]] | None = None,
) -> None:
    start = time.time()
    result = _call_or_skip(question, history=history)
    elapsed = round(time.time() - start, 3)

    status_code = result["status_code"]
    answer = (result.get("extracted_content") or "").strip()

    missing: list[str] = []
    ok = False
    error: str | None = None

    try:
        assert status_code == 200, f"HTTP {status_code}: {result.get('response')}"
        assert answer, f"Empty answer. Response: {result.get('response')}"
        if expected_elements:
            missing = _missing_elements(answer, expected_elements)
            assert not missing, f"Missing expected elements: {missing}\nAnswer:\n{answer}"
        ok = True
    except AssertionError as e:
        error = str(e)
        raise
    finally:
        kb_chat_results.append(
            {
                "test_name": test_name,
                "question": question,
                "expected": expected_elements,
                "answer": answer,
                "missing": missing,
                "ok": ok,
                "status_code": status_code,
                "elapsed_s": elapsed,
                "error": error,
            }
        )


def test_kb_chat_backend_connection(kb_chat_results: list[dict[str, Any]]):
    """最小连通性测试（后端可用 + 返回 200）。"""
    _run_case(
        kb_chat_results=kb_chat_results,
        test_name="backend connection",
        question="你好,我头痛,有什么方法",
        expected_elements=[],
    )


@pytest.mark.parametrize(
    "test_name,question,expected_elements",
    [
        (
            "precise price checking 精准查价测试",
            "AI天眼筛查多少钱？",
            ["50元", "47元", "34元", "10分钟"],
        ),
        (
            "健康方案咨询测试",
            "我最近总是失眠，睡不着，有什么调理方案吗？",
            ["小愈机器人睡眠专家模式", "律动床垫", "酸枣仁百合茯苓茶", "止鼾枕", "头部刮痧", "点穴"],
        ),
        (
            "会员制度理解测试",
            "我想办个钻石会员，多少钱？包含什么？",
            ["9880元/年", "不限次", "15次主题套餐", "85折"],
        ),
        (
            "联系方式测试",
            "你们店在哪里？我想预约赵老师。",
            ["北京市西城区广义街5号广益大厦B座308", "18611263770"],
        ),
        (
            "边界处理测试",
            "你们能做心脏搭桥手术吗？",
            ["健康调理机构", "不能", "手术"],
        ),
    ],
)
def test_kb_chat_cases(
    kb_chat_results: list[dict[str, Any]],
    test_name: str,
    question: str,
    expected_elements: list[str],
):
    """5 类验收题：用 pytest 断言验证关键点。"""
    _run_case(
        kb_chat_results=kb_chat_results,
        test_name=test_name,
        question=question,
        expected_elements=expected_elements,
    )


def test_kb_chat_multi_turn_dialogue(kb_chat_results: list[dict[str, Any]]):
    """考题5：多轮对话（历史上下文）。"""
    q1 = "那个护眼仪怎么卖？"
    r1 = _call_or_skip(q1)
    assert r1["status_code"] == 200
    a1 = (r1.get("extracted_content") or "").strip()
    assert a1

    kb_chat_results.append(
        {
            "test_name": "multi-turn (turn1)",
            "question": q1,
            "expected": [],
            "answer": a1,
            "missing": [],
            "ok": True,
            "status_code": r1["status_code"],
            "elapsed_s": None,
            "error": None,
        }
    )

    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": a1},
    ]

    q2 = "那它可以租吗？或者试用？"
    expected = ["试用", "押金", "0元"]

    _run_case(
        kb_chat_results=kb_chat_results,
        test_name="multi-turn (turn2)",
        question=q2,
        expected_elements=expected,
        history=history,
    )

