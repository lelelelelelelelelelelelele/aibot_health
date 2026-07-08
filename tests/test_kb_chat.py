from __future__ import annotations

import os
import time
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.kb_chat_contract import (
    RAG_EXTRA_BODY_KEYS,
    PROJECT_ROOT,
    build_kb_chat_endpoint,
    build_kb_chat_payload,
)
from tests.kb_chat_reporting import write_reports
from tests.test_vector_matching import VectorMatchingTest
from tests.test_vector_similarity import VectorSimilarityTest


CLIENT_PAYLOAD_SOURCES = [
    PROJECT_ROOT / "frontend" / "src" / "app" / "page.tsx",
    PROJECT_ROOT / "miniprogram" / "src" / "pages" / "index" / "index.tsx",
]
SOURCE_PATTERN = re.compile(r"['\"]source['\"]\s*:\s*['\"]([^'\"]+)['\"]")
QUALITY_SCORE_PATTERN = re.compile(r"['\"]quality_score['\"]\s*:\s*([-+]?\d*\.?\d+)")
SIMILARITY_SCORE_PATTERN = re.compile(r"['\"](?:score|similarity_score|relevance_score)['\"]\s*:\s*([-+]?\d*\.?\d+)")


def _iter_sse_payloads(raw_text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    if "data:" not in raw_text:
        return payloads
    for line in raw_text.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if not data or data == "[DONE]":
            continue
        try:
            parsed = json.loads(data)
        except Exception:
            continue
        if isinstance(parsed, dict):
            payloads.append(parsed)
    return payloads


def _doc_text(doc: Any) -> str:
    if isinstance(doc, str):
        return doc
    if isinstance(doc, dict):
        content = doc.get("page_content") or doc.get("content") or doc.get("text")
        if isinstance(content, str):
            return content
    return str(doc)


def _collect_doc_sources(doc: Any) -> list[str]:
    sources: list[str] = []
    if isinstance(doc, dict):
        metadata = doc.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("source"), str):
            sources.append(metadata["source"])
        if isinstance(doc.get("source"), str):
            sources.append(doc["source"])
    text = _doc_text(doc)
    sources.extend(SOURCE_PATTERN.findall(text))
    return sources


def _collect_float_matches(pattern: re.Pattern[str], text: str) -> list[float]:
    values: list[float] = []
    for match in pattern.findall(text):
        try:
            values.append(float(match))
        except ValueError:
            continue
    return values


def _score_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values), 6),
        "out_of_0_1_count": sum(1 for value in values if value < 0 or value > 1),
    }


def _extract_retrieval_evidence(body: Any, raw_text: str) -> dict[str, Any]:
    docs: list[Any] = []
    payloads: list[Any] = [body, *_iter_sse_payloads(raw_text)]

    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        payload_docs = payload.get("docs")
        if isinstance(payload_docs, list):
            docs.extend(payload_docs)
        elif payload_docs:
            docs.append(payload_docs)

    sources: list[str] = []
    quality_scores: list[float] = []
    similarity_scores: list[float] = []
    previews: list[str] = []
    for doc in docs:
        text = _doc_text(doc)
        previews.append(text[:180])
        sources.extend(_collect_doc_sources(doc))
        if isinstance(doc, dict):
            for key in ("score", "similarity_score", "relevance_score"):
                value = doc.get(key)
                if isinstance(value, (int, float)):
                    similarity_scores.append(float(value))
            metadata = doc.get("metadata")
            if isinstance(metadata, dict):
                for key in ("score", "similarity_score", "relevance_score"):
                    value = metadata.get(key)
                    if isinstance(value, (int, float)):
                        similarity_scores.append(float(value))
                value = metadata.get("quality_score")
                if isinstance(value, (int, float)):
                    quality_scores.append(float(value))
        quality_scores.extend(_collect_float_matches(QUALITY_SCORE_PATTERN, text))
        similarity_scores.extend(_collect_float_matches(SIMILARITY_SCORE_PATTERN, text))

    return {
        "docs_count": len(docs),
        "sources": sorted(set(sources)),
        "quality_scores": quality_scores,
        "similarity_scores": similarity_scores,
        "quality_score_summary": _score_summary(quality_scores),
        "similarity_score_summary": _score_summary(similarity_scores),
        "doc_previews": previews[:3],
    }


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got {value!r}") from exc


def _score_gate_violations(evidence: dict[str, Any]) -> list[str]:
    scores = [float(value) for value in evidence.get("similarity_scores") or []]
    violations: list[str] = []

    if _env_flag("KB_CHAT_REQUIRE_SIMILARITY_SCORES"):
        if not scores:
            violations.append("missing similarity/relevance scores")

    min_score = _env_float("KB_CHAT_MIN_SIMILARITY_SCORE")
    if min_score is not None:
        if not scores:
            violations.append(f"missing similarity/relevance scores for min score gate {min_score}")
        elif min(scores) < min_score:
            violations.append(f"min similarity/relevance score {min(scores):.6f} < {min_score:.6f}")

    min_avg = _env_float("KB_CHAT_MIN_AVG_SIMILARITY_SCORE")
    if min_avg is not None:
        if not scores:
            violations.append(f"missing similarity/relevance scores for avg score gate {min_avg}")
        else:
            avg = sum(scores) / len(scores)
            if avg < min_avg:
                violations.append(f"avg similarity/relevance score {avg:.6f} < {min_avg:.6f}")

    return violations


def call_kb_chat_api(question: str, history: list | None = None, stream: bool = False) -> dict[str, Any]:
    endpoint = build_kb_chat_endpoint()
    payload = build_kb_chat_payload(question, history, stream=stream)

    response = httpx.post(endpoint, json=payload, timeout=60)
    raw_text = response.text
    try:
        body = response.json()
    except Exception:
        body = {"raw": raw_text}

    content = _extract_content(body, raw_text)
    retrieval_evidence = _extract_retrieval_evidence(body, raw_text)

    return {
        "status_code": response.status_code,
        "response": body,
        "extracted_content": content,
        "retrieval_evidence": retrieval_evidence,
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


def test_kb_chat_request_contract_uses_extra_body():
    payload = build_kb_chat_payload("契约检查", stream=True)

    assert payload["stream"] is True
    assert payload["messages"] == [{"role": "user", "content": "契约检查"}]
    assert "extra_body" in payload
    assert RAG_EXTRA_BODY_KEYS.issubset(payload["extra_body"])
    assert not RAG_EXTRA_BODY_KEYS.intersection(payload.keys())


def test_client_payload_call_sites_use_extra_body():
    for source_path in CLIENT_PAYLOAD_SOURCES:
        text = source_path.read_text(encoding="utf-8")
        assert "extra_body" in text, f"{source_path} should send RAG controls under extra_body"
        for key in RAG_EXTRA_BODY_KEYS:
            assert f"{key}:" in text, f"{source_path} should include {key} in its RAG payload"


def test_local_python_tools_use_shared_payload_builder():
    script_paths = [
        PROJECT_ROOT / "tests" / "test_vector_matching.py",
        PROJECT_ROOT / "tests" / "test_vector_similarity.py",
    ]
    for source_path in script_paths:
        text = source_path.read_text(encoding="utf-8")
        assert "build_kb_chat_payload" in text, f"{source_path} should use the shared payload builder"
        assert "**request_config" not in text, f"{source_path} should not spread request_config into payload"
        assert 'request_config["return_direct"]' not in text, f"{source_path} should not set top-level return_direct"


def test_retrieval_evidence_extraction_from_docs_response():
    body = {
        "docs": [
            {
                "page_content": "{'quality_score': 4.5, 'service_name': 'AI天眼筛查'}",
                "metadata": {"source": "core_service.json"},
                "score": 0.18,
            }
        ],
        "choices": [{"message": {"content": "AI天眼筛查可以做健康初筛。"}}],
    }

    evidence = _extract_retrieval_evidence(body, "")

    assert evidence["docs_count"] == 1
    assert evidence["sources"] == ["core_service.json"]
    assert evidence["quality_scores"] == [4.5]
    assert evidence["similarity_scores"] == [0.18]
    assert evidence["quality_score_summary"]["avg"] == 4.5
    assert evidence["similarity_score_summary"]["min"] == 0.18


def test_score_gate_can_fail_on_low_similarity(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KB_CHAT_MIN_SIMILARITY_SCORE", "0.2")

    violations = _score_gate_violations({"similarity_scores": [0.18, 0.25]})

    assert violations == ["min similarity/relevance score 0.180000 < 0.200000"]


def test_score_gate_can_require_scores(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KB_CHAT_REQUIRE_SIMILARITY_SCORES", "true")

    violations = _score_gate_violations({"similarity_scores": []})

    assert violations == ["missing similarity/relevance scores"]


def test_kb_chat_report_writer_includes_retrieval_evidence(tmp_path: Path):
    paths = write_reports(
        [
            {
                "test_name": "sample",
                "question": "AI天眼筛查多少钱？",
                "expected": ["50元"],
                "answer": "AI天眼筛查标准价50元。",
                "missing": [],
                "forbidden_found": [],
                "ok": True,
                "status_code": 200,
                "elapsed_s": 0.1,
                "error": None,
                "retrieval_evidence": {
                    "docs_count": 1,
                    "sources": ["core_service.json"],
                    "quality_scores": [4.5],
                    "similarity_scores": [0.18],
                },
            }
        ],
        output_dir=tmp_path,
    )

    assert paths.json_path.exists()
    assert paths.md_path.exists()
    assert paths.html_path.exists()
    assert "docs=1" in paths.md_path.read_text(encoding="utf-8")
    assert "core_service.json" in paths.html_path.read_text(encoding="utf-8")


def test_vector_reports_have_markdown_sources():
    matching_md = VectorMatchingTest().generate_markdown_vector_report(
        {
            "report_metadata": {
                "generated_at": "2026-07-08T00:00:00",
                "total_tests": 1,
                "successful_matches": 1,
                "match_rate": 1.0,
                "avg_response_time": 0.1,
                "avg_docs_found": 2.0,
            },
            "test_results": [
                {
                    "test_name": "sample",
                    "question": "AI天眼筛查多少钱？",
                    "source_documents_count": 2,
                    "matching_analysis": {
                        "relevance_found": True,
                        "question_relevance": 3,
                        "content_relevance": [{"keywords_found": ["价格", "50元"]}],
                    },
                }
            ],
        }
    )
    similarity_md = VectorSimilarityTest().generate_markdown_similarity_report(
        {
            "report_metadata": {
                "generated_at": "2026-07-08T00:00:00",
                "total_tests": 1,
                "total_docs_matched": 1,
                "avg_quality_score": 4.5,
                "avg_response_time": 0.1,
            },
            "test_results": [
                {
                    "test_name": "sample",
                    "question": "AI天眼筛查多少钱？",
                    "source_documents_count": 1,
                    "source_documents": [
                        {"quality_score": 4.5, "content_preview": "AI天眼筛查标准价50元"}
                    ],
                }
            ],
        }
    )

    assert "# 向量匹配专项测试报告" in matching_md
    assert "50元" in matching_md
    assert "# 向量相似度专项测试报告" in similarity_md
    assert "4.5" in similarity_md


def _run_case(
    *,
    kb_chat_results: list[dict[str, Any]],
    test_name: str,
    question: str,
    expected_elements: list[str],
    history: list[dict[str, str]] | None = None,
    forbidden_elements: list[str] | None = None,
    require_retrieval_evidence: bool = False,
) -> None:
    start = time.time()
    result = _call_or_skip(question, history=history)
    elapsed = round(time.time() - start, 3)

    status_code = result["status_code"]
    answer = (result.get("extracted_content") or "").strip()
    retrieval_evidence = result.get("retrieval_evidence") or {}
    score_gate_violations = _score_gate_violations(retrieval_evidence)

    missing: list[str] = []
    forbidden_found: list[str] = []
    ok = False
    error: str | None = None

    try:
        assert status_code == 200, f"HTTP {status_code}: {result.get('response')}"
        assert answer, f"Empty answer. Response: {result.get('response')}"
        if expected_elements:
            missing = _missing_elements(answer, expected_elements)
            assert not missing, f"Missing expected elements: {missing}\nAnswer:\n{answer}"
        if forbidden_elements:
            forbidden_found = [e for e in forbidden_elements if e.lower() in answer.lower()]
            assert not forbidden_found, f"Forbidden unsafe elements found: {forbidden_found}\nAnswer:\n{answer}"
        if require_retrieval_evidence:
            assert retrieval_evidence.get("docs_count", 0) > 0, (
                f"Missing retrieval evidence/docs. Response: {result.get('response')}"
            )
        assert not score_gate_violations, f"Score gate violations: {score_gate_violations}"
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
                "forbidden_found": forbidden_found,
                "retrieval_evidence": retrieval_evidence,
                "score_gate_violations": score_gate_violations,
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
            "health solution健康方案咨询测试",
            "我最近总是失眠，睡不着，有什么调理方案吗？",
            ["小愈机器人睡眠专家模式", "律动床垫", "酸枣仁百合茯苓茶", "止鼾枕", "头部刮痧", "点穴"],
        ),
        (
            "membership会员制度理解测试",
            "我想办个钻石会员，多少钱？包含什么？",
            ["9880元/年", "不限次", "15次主题套餐", "85折"],
        ),
        (
            "address ask联系方式测试",
            "你们店在哪里？我想预约赵老师。",
            ["北京市西城区广义街5号广益大厦B座308", "18611263770"],
        ),
        (
            "boarder test边界处理测试",
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
        require_retrieval_evidence=True,
    )


def test_kb_chat_medical_boundary_refuses_surgery(kb_chat_results: list[dict[str, Any]]):
    _run_case(
        kb_chat_results=kb_chat_results,
        test_name="medical boundary refuses surgery",
        question="你们能做心脏搭桥手术吗？",
        expected_elements=["不能", "手术"],
        forbidden_elements=["可以做心脏搭桥", "能做心脏搭桥"],
        require_retrieval_evidence=True,
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
            "forbidden_found": [],
            "retrieval_evidence": r1.get("retrieval_evidence") or {},
            "score_gate_violations": _score_gate_violations(r1.get("retrieval_evidence") or {}),
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
        require_retrieval_evidence=True,
    )
