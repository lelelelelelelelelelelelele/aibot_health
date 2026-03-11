from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests

try:
    from tests.chat_response_parsing import extract_content_from_payload, extract_docs_from_payload, extract_error_from_payload
except ModuleNotFoundError:
    from chat_response_parsing import extract_content_from_payload, extract_docs_from_payload, extract_error_from_payload


DEFAULT_ENDPOINT = "https://api.cpagz.com/knowledge_base/local_kb/health%20clinic/chat/completions"
DEFAULT_PROMPT = "AI天眼筛查多少钱？"
FULL_MODELS = [
    "Qwen/Qwen3.5-397B-A17B",
    "MiniMax/MiniMax-M2.5",
    "moonshotai/Kimi-K2.5",
    "Qwen/Qwen3.5-122B-A10B",
    "Qwen/Qwen3.5-27B",
    "Qwen/Qwen3.5-35B-A3B",
    "ZhipuAI/GLM-4.7-Flash",
    "ZhipuAI/GLM-5",
    "qwen3.5-flash-2026-02-23",
]
CANDIDATE_MODELS = [
    "ZhipuAI/GLM-4.7-Flash",
    "Qwen/Qwen3.5-27B",
    "qwen3-max",
    "kimi-k2-0905",
]
DEFAULT_MODELS = CANDIDATE_MODELS
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "artifacts"
FOCUS_MODEL = "Qwen/Qwen3.5-397B-A17B"


def _ms_between(start: float, end: float) -> float:
    return round((end - start) * 1000.0, 3)


def _safe_round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def _decode_line(line: bytes | str) -> str:
    if isinstance(line, bytes):
        return line.decode("utf-8", errors="replace")
    return line


def _is_ping_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(":") or stripped.lower() == "ping"


def _metric_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "avg": None, "max": None}
    return {
        "min": _safe_round(min(values)),
        "avg": _safe_round(sum(values) / len(values)),
        "max": _safe_round(max(values)),
    }


def _sort_key(row: dict[str, Any]) -> tuple[float, str]:
    avg = row["first_non_empty_content_ms"]["avg"]
    return (math.inf if avg is None else avg, row["model"])


def run_single_benchmark(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    run_index: int,
    request_sender: Callable[..., Any] = requests.post,
    now: Callable[[], float] = time.perf_counter,
    timeout: float = 90.0,
    max_content_events: int = 2,
) -> dict[str, Any]:
    started_at = now()
    last_observed_at = started_at
    response = None
    result = {
        "model": model,
        "run_index": run_index,
        "status_code": None,
        "connect_or_headers_ms": None,
        "first_sse_event_ms": None,
        "first_docs_ms": None,
        "first_non_empty_content_ms": None,
        "total_ms": None,
        "content_chars": 0,
        "event_count": 0,
        "content_events": 0,
        "error": None,
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    try:
        response = request_sender(
            url=endpoint,
            headers=DEFAULT_HEADERS,
            json=payload,
            stream=True,
            timeout=timeout,
        )
        last_observed_at = now()
        result["status_code"] = getattr(response, "status_code", None)
        result["connect_or_headers_ms"] = _ms_between(started_at, last_observed_at)

        for raw_line in response.iter_lines():
            decoded = _decode_line(raw_line).strip()
            if not decoded or _is_ping_line(decoded):
                continue
            if not decoded.startswith("data:"):
                continue

            observed_at = now()
            last_observed_at = observed_at

            data_payload = decoded[len("data:") :].strip()
            if not data_payload or data_payload == "[DONE]":
                if data_payload == "[DONE]":
                    break
                continue
            if data_payload.lower() == "ping":
                continue

            result["event_count"] += 1
            if result["first_sse_event_ms"] is None:
                result["first_sse_event_ms"] = _ms_between(started_at, observed_at)

            if result["first_docs_ms"] is None and extract_docs_from_payload(data_payload):
                result["first_docs_ms"] = _ms_between(started_at, observed_at)

            event_error = extract_error_from_payload(data_payload)
            if event_error and result["error"] is None:
                result["error"] = event_error

            content = extract_content_from_payload(data_payload)
            if not content:
                continue

            result["content_events"] += 1
            result["content_chars"] += len(content)
            if result["first_non_empty_content_ms"] is None:
                result["first_non_empty_content_ms"] = _ms_between(started_at, observed_at)

            if result["content_events"] >= max_content_events:
                break
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()
        try:
            finished_at = now()
        except StopIteration:
            finished_at = last_observed_at
        result["total_ms"] = _ms_between(started_at, finished_at)

    return result


def summarize_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["model"]].append(result)

    summary_rows: list[dict[str, Any]] = []
    for model, entries in grouped.items():
        connect_values = [entry["connect_or_headers_ms"] for entry in entries if entry["connect_or_headers_ms"] is not None]
        first_event_values = [entry["first_sse_event_ms"] for entry in entries if entry["first_sse_event_ms"] is not None]
        first_docs_values = [entry["first_docs_ms"] for entry in entries if entry["first_docs_ms"] is not None]
        first_content_values = [entry["first_non_empty_content_ms"] for entry in entries if entry["first_non_empty_content_ms"] is not None]
        total_values = [entry["total_ms"] for entry in entries if entry["total_ms"] is not None]

        summary_rows.append(
            {
                "model": model,
                "runs": len(entries),
                "successful_runs": sum(
                    1
                    for entry in entries
                    if entry.get("error") is None and entry.get("status_code") in (None, 200)
                ),
                "first_content_runs": len(first_content_values),
                "connect_or_headers_ms": _metric_stats(connect_values),
                "first_sse_event_ms": _metric_stats(first_event_values),
                "first_docs_ms": _metric_stats(first_docs_values),
                "first_non_empty_content_ms": _metric_stats(first_content_values),
                "total_ms": _metric_stats(total_values),
                "errors": [entry["error"] for entry in entries if entry.get("error")],
            }
        )

    return sorted(summary_rows, key=_sort_key)


def build_report_payload(
    *,
    endpoint: str,
    prompt: str,
    runs: int,
    models: list[str],
    max_content_events: int,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "endpoint": endpoint,
        "prompt": prompt,
        "runs": runs,
        "models": models,
        "max_content_events": max_content_events,
        "summary": summarize_results(results),
        "results": results,
    }


def render_summary_table(summary_rows: list[dict[str, Any]]) -> str:
    headers = [
        "model",
        "runs",
        "ok",
        "first_docs_avg",
        "first_content(min/avg/max)",
        "headers_avg",
        "first_event_avg",
        "total_avg",
    ]
    lines = [" | ".join(headers), "-|-".join("-" * len(header) for header in headers)]

    for row in summary_rows:
        first_content = row["first_non_empty_content_ms"]
        lines.append(
            " | ".join(
                [
                    row["model"],
                    str(row["runs"]),
                    f"{row['successful_runs']}/{row['runs']}",
                    _format_value(row["first_docs_ms"]["avg"]),
                    _format_stats(first_content),
                    _format_value(row["connect_or_headers_ms"]["avg"]),
                    _format_value(row["first_sse_event_ms"]["avg"]),
                    _format_value(row["total_ms"]["avg"]),
                ]
            )
        )

    return "\n".join(lines)


def generate_diagnosis(summary_rows: list[dict[str, Any]], focus_model: str = FOCUS_MODEL) -> list[str]:
    if not summary_rows:
        return ["No results collected."]

    diagnosis: list[str] = []
    focus_row = next((row for row in summary_rows if row["model"] == focus_model), None)
    avg_header_values = [row["connect_or_headers_ms"]["avg"] for row in summary_rows if row["connect_or_headers_ms"]["avg"] is not None]
    avg_docs_values = [row["first_docs_ms"]["avg"] for row in summary_rows if row["first_docs_ms"]["avg"] is not None]
    avg_event_values = [row["first_sse_event_ms"]["avg"] for row in summary_rows if row["first_sse_event_ms"]["avg"] is not None]

    if avg_header_values and min(avg_header_values) >= 2000:
        diagnosis.append("Most models have slow header/connect time. The bottleneck likely sits in the online chain or gateway.")
    if avg_docs_values and min(avg_docs_values) >= 3000:
        diagnosis.append("Most models are slow to return docs. Retrieval or embedding likely dominates before generation starts.")
    if avg_event_values and min(avg_event_values) >= 2500:
        diagnosis.append("Most models are also slow to emit the first SSE event. The gateway or upstream queue is a stronger suspect than any single model.")

    if focus_row:
        focus_docs_avg = focus_row["first_docs_ms"]["avg"]
        focus_content_avg = focus_row["first_non_empty_content_ms"]["avg"]
        focus_header_avg = focus_row["connect_or_headers_ms"]["avg"]
        other_rows = [row for row in summary_rows if row["model"] != focus_model]
        other_docs_avgs = [row["first_docs_ms"]["avg"] for row in other_rows if row["first_docs_ms"]["avg"] is not None]
        other_content_avgs = [row["first_non_empty_content_ms"]["avg"] for row in other_rows if row["first_non_empty_content_ms"]["avg"] is not None]
        other_header_avgs = [row["connect_or_headers_ms"]["avg"] for row in other_rows if row["connect_or_headers_ms"]["avg"] is not None]

        if focus_docs_avg is not None and other_docs_avgs:
            baseline_docs = sum(other_docs_avgs) / len(other_docs_avgs)
            if focus_docs_avg > baseline_docs * 1.5:
                diagnosis.append(
                    f"{focus_model} is already slower on docs retrieval than peer models. Retrieval or upstream preprocessing may be part of the delay."
                )

        if focus_content_avg is not None and other_content_avgs:
            baseline_content = sum(other_content_avgs) / len(other_content_avgs)
            header_gap = None
            if focus_header_avg is not None and other_header_avgs:
                header_gap = abs(focus_header_avg - (sum(other_header_avgs) / len(other_header_avgs)))

            if focus_content_avg > baseline_content * 1.5 and (header_gap is None or header_gap <= 300):
                diagnosis.append(
                    f"{focus_model} is much slower on first non-empty content while header time stays comparable. This points more to model generation latency."
                )

        focus_event_avg = focus_row["first_sse_event_ms"]["avg"]
        if (
            focus_content_avg is not None
            and focus_docs_avg is not None
            and focus_content_avg - focus_docs_avg >= 2000
        ):
            diagnosis.append(
                f"{focus_model} returns docs noticeably earlier than reply content. Retrieval is fast enough, and the remaining delay is more likely generation time."
            )

    if not diagnosis:
        diagnosis.append("No single bottleneck stands out yet. Compare per-run JSON to separate transient network variance from stable model latency.")

    return diagnosis


def _format_value(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}ms"


def _format_stats(stats: dict[str, float | None]) -> str:
    return "/".join(
        [
            _format_value(stats["min"]),
            _format_value(stats["avg"]),
            _format_value(stats["max"]),
        ]
    )


def _normalize_models(raw_models: list[str] | None, *, use_full_models: bool = False) -> list[str]:
    fallback_models = FULL_MODELS if use_full_models else DEFAULT_MODELS
    if not raw_models:
        return list(fallback_models)

    normalized: list[str] = []
    for value in raw_models:
        for item in value.split(","):
            model = item.strip()
            if model:
                normalized.append(model)
    return normalized or list(fallback_models)


def load_resumed_results(
    resume_paths: list[str | Path] | None,
    *,
    models: list[str],
    runs: int,
) -> list[dict[str, Any]]:
    if not resume_paths:
        return []

    model_set = set(models)
    seen_runs: set[tuple[str, int]] = set()
    resumed_results: list[dict[str, Any]] = []

    for raw_path in resume_paths:
        report_path = Path(raw_path)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        for entry in payload.get("results", []):
            if not isinstance(entry, dict):
                continue
            model = entry.get("model")
            run_index = entry.get("run_index")
            if model not in model_set or not isinstance(run_index, int):
                continue
            if run_index < 1 or run_index > runs:
                continue
            key = (model, run_index)
            if key in seen_runs:
                continue
            seen_runs.add(key)
            resumed_results.append(entry)

    return resumed_results


def plan_benchmark_runs(
    *,
    models: list[str],
    runs: int,
    resumed_results: list[dict[str, Any]],
) -> list[tuple[str, int]]:
    completed = {
        (entry.get("model"), entry.get("run_index"))
        for entry in resumed_results
        if isinstance(entry, dict)
    }

    pending: list[tuple[str, int]] = []
    for model in models:
        for run_index in range(1, runs + 1):
            if (model, run_index) not in completed:
                pending.append((model, run_index))
    return pending


def _sort_results_for_output(results: list[dict[str, Any]], models: list[str]) -> list[dict[str, Any]]:
    model_order = {model: index for index, model in enumerate(models)}
    return sorted(
        results,
        key=lambda entry: (
            model_order.get(str(entry.get("model")), len(model_order)),
            int(entry.get("run_index", 0) or 0),
        ),
    )


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"sse_benchmark_{timestamp}.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark first non-empty SSE content latency across models.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="SSE chat completions endpoint.")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per model.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Fixed benchmark prompt.")
    parser.add_argument("--models", nargs="*", default=None, help="Override model list. Accepts repeated values or comma-separated models.")
    parser.add_argument("--full-models", action="store_true", help="Use the full model list instead of the default candidate set.")
    parser.add_argument("--output", default=None, help="Write JSON report to this path. Defaults to tests/artifacts timestamped JSON.")
    parser.add_argument("--resume-from", nargs="+", default=None, help="Reuse results from one or more existing JSON reports and only run missing model/round pairs.")
    parser.add_argument("--max-content-events", type=int, default=2, help="Stop after receiving this many non-empty content events.")
    parser.add_argument("--timeout", type=float, default=90.0, help="Request timeout in seconds.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    models = _normalize_models(args.models, use_full_models=args.full_models)
    output_path = Path(args.output) if args.output else _default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("SSE first-content latency benchmark")
    print(f"Endpoint: {args.endpoint}")
    print(f"Prompt: {args.prompt}")
    print(f"Runs per model: {args.runs}")
    print(f"Max content events per run: {args.max_content_events}")
    print(f"Models: {len(models)}")
    if args.resume_from:
        print(f"Resume reports: {len(args.resume_from)}")

    resumed_results = load_resumed_results(args.resume_from, models=models, runs=args.runs)
    pending_runs = plan_benchmark_runs(models=models, runs=args.runs, resumed_results=resumed_results)
    results: list[dict[str, Any]] = list(resumed_results)

    if resumed_results:
        print(f"Reused prior runs: {len(resumed_results)}")

    for model in models:
        model_pending_runs = [run_index for pending_model, run_index in pending_runs if pending_model == model]
        if not model_pending_runs:
            print(f"\n== {model} ==")
            print("all requested runs reused from prior reports")
            continue

        print(f"\n== {model} ==")
        for run_index in model_pending_runs:
            result = run_single_benchmark(
                endpoint=args.endpoint,
                model=model,
                prompt=args.prompt,
                run_index=run_index,
                timeout=args.timeout,
                max_content_events=args.max_content_events,
            )
            results.append(result)
            print(
                f"run {run_index}: status={result['status_code']} "
                f"headers={_format_value(result['connect_or_headers_ms'])} "
                f"first_event={_format_value(result['first_sse_event_ms'])} "
                f"first_docs={_format_value(result['first_docs_ms'])} "
                f"first_content={_format_value(result['first_non_empty_content_ms'])} "
                f"total={_format_value(result['total_ms'])} "
                f"content_events={result['content_events']} "
                f"error={result['error'] or '-'}"
            )

    results = _sort_results_for_output(results, models)
    summary = summarize_results(results)
    payload = build_report_payload(
        endpoint=args.endpoint,
        prompt=args.prompt,
        runs=args.runs,
        models=models,
        max_content_events=args.max_content_events,
        results=results,
    )
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSummary")
    print(render_summary_table(summary))

    print("\nDiagnosis")
    for line in generate_diagnosis(summary):
        print(f"- {line}")

    print(f"\nJSON report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
