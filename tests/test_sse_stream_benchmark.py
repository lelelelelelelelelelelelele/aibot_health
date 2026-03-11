from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("test_sse_stream.py")
SPEC = importlib.util.spec_from_file_location("sse_benchmark_module", MODULE_PATH)
assert SPEC and SPEC.loader
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


class FakeResponse:
    def __init__(self, lines: list[bytes], status_code: int = 200):
        self._lines = lines
        self.status_code = status_code

    def iter_lines(self):
        for line in self._lines:
            yield line

    def close(self):
        return None


def test_run_single_benchmark_tracks_first_content_and_ignores_ping():
    start_points = iter([10.0, 10.15, 10.4, 10.9, 11.5, 11.8])
    lines = [
        b": ping - keepalive",
        b"data: {\"docs\": [{\"id\": 1}], \"choices\": [{\"delta\": {\"content\": \"\"}}]}",
        b"data: {\"choices\": [{\"delta\": {\"content\": \"AI\"}}]}",
        b"data: [DONE]",
    ]
    response = FakeResponse(lines=lines)

    result = BENCHMARK.run_single_benchmark(
        endpoint="https://example.com/chat/completions",
        model="Qwen/Qwen3.5-397B-A17B",
        prompt="AI天眼筛查多少钱？",
        run_index=1,
        request_sender=lambda **_: response,
        now=lambda: next(start_points),
        max_content_events=2,
    )

    assert result["status_code"] == 200
    assert result["event_count"] == 2
    assert result["content_events"] == 1
    assert result["content_chars"] == 2
    assert result["connect_or_headers_ms"] == 150.0
    assert result["first_sse_event_ms"] == 400.0
    assert result["first_docs_ms"] == 400.0
    assert result["first_non_empty_content_ms"] == 900.0
    assert result["total_ms"] == 1800.0
    assert result["error"] is None


def test_run_single_benchmark_extracts_content_from_json_string_payload():
    start_points = iter([20.0, 20.1, 20.3, 20.8, 21.0])
    lines = [
        b'data: "{\\"choices\\":[{\\"message\\":{\\"content\\":\\"\\u8fde\\u63a5\\u6b63\\u5e38\\"}}]}"',
        b"data: [DONE]",
    ]
    response = FakeResponse(lines=lines)

    result = BENCHMARK.run_single_benchmark(
        endpoint="https://example.com/chat/completions",
        model="Qwen/Qwen3.5-397B-A17B",
        prompt="AI天眼筛查多少钱？",
        run_index=1,
        request_sender=lambda **_: response,
        now=lambda: next(start_points),
        max_content_events=1,
    )

    assert result["first_non_empty_content_ms"] == 300.0
    assert result["content_events"] == 1
    assert result["content_chars"] == 4
    assert result["error"] is None


def test_summarize_results_orders_models_by_first_content_average():
    results = [
        {"model": "slow", "first_docs_ms": 900.0, "first_non_empty_content_ms": 3000.0, "connect_or_headers_ms": 400.0, "first_sse_event_ms": 500.0, "total_ms": 6000.0, "error": None},
        {"model": "slow", "first_docs_ms": 950.0, "first_non_empty_content_ms": 3300.0, "connect_or_headers_ms": 450.0, "first_sse_event_ms": 520.0, "total_ms": 6200.0, "error": None},
        {"model": "fast", "first_docs_ms": 450.0, "first_non_empty_content_ms": 800.0, "connect_or_headers_ms": 380.0, "first_sse_event_ms": 420.0, "total_ms": 1400.0, "error": None},
        {"model": "fast", "first_docs_ms": 500.0, "first_non_empty_content_ms": 900.0, "connect_or_headers_ms": 390.0, "first_sse_event_ms": 430.0, "total_ms": 1500.0, "error": None},
    ]

    summary = BENCHMARK.summarize_results(results)

    assert [row["model"] for row in summary] == ["fast", "slow"]
    assert summary[0]["first_docs_ms"]["avg"] == 475.0
    assert summary[0]["first_non_empty_content_ms"]["avg"] == 850.0
    assert summary[1]["first_non_empty_content_ms"]["max"] == 3300.0
    assert summary[0]["successful_runs"] == 2


def test_build_json_report_includes_metadata_and_raw_results():
    results = [
        {
            "model": "fast",
            "run_index": 1,
            "status_code": 200,
            "connect_or_headers_ms": 120.0,
            "first_sse_event_ms": 220.0,
            "first_docs_ms": 260.0,
            "first_non_empty_content_ms": 420.0,
            "total_ms": 800.0,
            "content_chars": 6,
            "event_count": 3,
            "content_events": 1,
            "error": None,
        }
    ]

    payload = BENCHMARK.build_report_payload(
        endpoint="https://example.com/chat/completions",
        prompt="AI天眼筛查多少钱？",
        runs=3,
        models=["fast"],
        max_content_events=2,
        results=results,
    )

    assert payload["endpoint"] == "https://example.com/chat/completions"
    assert payload["prompt"] == "AI天眼筛查多少钱？"
    assert payload["runs"] == 3
    assert payload["models"] == ["fast"]
    assert payload["max_content_events"] == 2
    assert payload["results"] == results
    json.dumps(payload, ensure_ascii=False)


def test_normalize_models_defaults_to_candidate_model_set():
    assert BENCHMARK._normalize_models(None) == [
        "ZhipuAI/GLM-4.7-Flash",
        "Qwen/Qwen3.5-27B",
        "qwen3-max",
        "kimi-k2-0905",
    ]


def test_load_resumed_results_filters_models_and_deduplicates_runs(tmp_path: Path):
    first_report = tmp_path / "first.json"
    first_report.write_text(
        json.dumps(
            {
                "results": [
                    {"model": "ZhipuAI/GLM-4.7-Flash", "run_index": 1, "status_code": 200},
                    {"model": "Qwen/Qwen3.5-27B", "run_index": 1, "status_code": 200},
                    {"model": "qwen3.5-flash-2026-02-23", "run_index": 1, "status_code": 200},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    second_report = tmp_path / "second.json"
    second_report.write_text(
        json.dumps(
            {
                "results": [
                    {"model": "qwen3-max", "run_index": 1, "status_code": 200},
                    {"model": "qwen3-max", "run_index": 1, "status_code": 500},
                    {"model": "kimi-k2-0905", "run_index": 2, "status_code": 200},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    resumed = BENCHMARK.load_resumed_results(
        [first_report, second_report],
        models=[
            "ZhipuAI/GLM-4.7-Flash",
            "Qwen/Qwen3.5-27B",
            "qwen3-max",
            "kimi-k2-0905",
        ],
        runs=1,
    )

    assert resumed == [
        {"model": "ZhipuAI/GLM-4.7-Flash", "run_index": 1, "status_code": 200},
        {"model": "Qwen/Qwen3.5-27B", "run_index": 1, "status_code": 200},
        {"model": "qwen3-max", "run_index": 1, "status_code": 200},
    ]


def test_plan_benchmark_runs_only_returns_missing_candidate_runs():
    resumed_results = [
        {"model": "ZhipuAI/GLM-4.7-Flash", "run_index": 1},
        {"model": "Qwen/Qwen3.5-27B", "run_index": 1},
        {"model": "qwen3-max", "run_index": 1},
    ]

    pending = BENCHMARK.plan_benchmark_runs(
        models=BENCHMARK._normalize_models(None),
        runs=1,
        resumed_results=resumed_results,
    )

    assert pending == [("kimi-k2-0905", 1)]


def test_parse_args_supports_multiple_resume_files(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "test_sse_stream.py",
            "--resume-from",
            "tests/artifacts/sse_small_models_smoke.json",
            "tests/artifacts/sse_qwen3_max_smoke.json",
        ],
    )

    args = BENCHMARK.parse_args()

    assert args.resume_from == [
        "tests/artifacts/sse_small_models_smoke.json",
        "tests/artifacts/sse_qwen3_max_smoke.json",
    ]
