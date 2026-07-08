from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ReportPaths:
    json_path: Path
    md_path: Path
    html_path: Path


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_reports(results: list[dict[str, Any]], output_dir: str | Path = "test_reports") -> ReportPaths:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    json_path = out_dir / f"kb_chat_test_report_{ts}.json"
    md_path = out_dir / f"kb_chat_test_report_{ts}.md"
    html_path = out_dir / f"kb_chat_test_report_{ts}.html"

    total = len(results)
    passed = sum(1 for r in results if r.get("ok") is True)
    failed = total - passed
    pass_rate = (passed / total * 100.0) if total else 0.0

    report = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "pass_rate": pass_rate,
        },
        "test_results": results,
    }

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    html_path.write_text(_to_html(report), encoding="utf-8")

    return ReportPaths(json_path=json_path, md_path=md_path, html_path=html_path)


def _evidence_summary(result: dict[str, Any]) -> str:
    evidence = result.get("retrieval_evidence") or {}
    docs_count = evidence.get("docs_count", 0)
    sources = evidence.get("sources") or []
    quality_scores = evidence.get("quality_scores") or []
    similarity_scores = evidence.get("similarity_scores") or []
    quality_summary = evidence.get("quality_score_summary") or {}
    similarity_summary = evidence.get("similarity_score_summary") or {}
    score_gate_violations = result.get("score_gate_violations") or []
    parts = [f"docs={docs_count}"]
    if sources:
        parts.append(f"sources={', '.join(str(s) for s in sources[:5])}")
    if quality_scores:
        parts.append(f"quality={quality_scores}")
    if quality_summary.get("count"):
        parts.append(
            "quality_summary="
            f"min:{quality_summary.get('min')},avg:{quality_summary.get('avg')},max:{quality_summary.get('max')}"
        )
    if similarity_scores:
        parts.append(f"scores={similarity_scores}")
    if similarity_summary.get("count"):
        parts.append(
            "score_summary="
            f"min:{similarity_summary.get('min')},avg:{similarity_summary.get('avg')},max:{similarity_summary.get('max')},"
            f"out_of_0_1:{similarity_summary.get('out_of_0_1_count', 0)}"
        )
    if score_gate_violations:
        parts.append(f"score_gate={'; '.join(str(v) for v in score_gate_violations)}")
    return "; ".join(parts)


def _to_markdown(report: dict[str, Any]) -> str:
    meta = report.get("report_metadata", {})
    lines = [
        "# KB Chat Pytest Report",
        "",
        f"- Generated at: {meta.get('generated_at', '')}",
        f"- Total: {meta.get('total_tests', 0)}",
        f"- Passed: {meta.get('passed_tests', 0)}",
        f"- Failed: {meta.get('failed_tests', 0)}",
        f"- Pass rate: {meta.get('pass_rate', 0):.2f}%",
        "",
        "| # | Case | Status | Question | Missing | Forbidden | Retrieval Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, result in enumerate(report.get("test_results", []), start=1):
        status = "PASS" if result.get("ok") is True else "FAIL"
        missing = json.dumps(result.get("missing", []), ensure_ascii=False)
        forbidden = json.dumps(result.get("forbidden_found", []), ensure_ascii=False)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    _md_cell(str(result.get("test_name", ""))),
                    status,
                    _md_cell(str(result.get("question", ""))),
                    _md_cell(missing),
                    _md_cell(forbidden),
                    _md_cell(_evidence_summary(result)),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _to_html(report: dict[str, Any]) -> str:
    meta = report.get("report_metadata", {})
    rows = []
    for i, r in enumerate(report.get("test_results", []), start=1):
        ok = bool(r.get("ok"))
        status = "通过" if ok else "失败"
        evidence = _evidence_summary(r)
        rows.append(
            "".join(
                [
                    f"<tr>",
                    f"<td>{i}</td>",
                    f"<td>{_esc(str(r.get('test_name', '')))}</td>",
                    f"<td>{_esc(str(r.get('question', '')))}</td>",
                    f"<td>{status}</td>",
                    f"<td>{_esc(str(r.get('elapsed_s', '')))}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(evidence)}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(str(r.get('answer', '')))}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(json.dumps(r.get('missing', []), ensure_ascii=False))}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(json.dumps(r.get('forbidden_found', []), ensure_ascii=False))}</td>",
                    f"</tr>",
                ]
            )
        )

    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>KB Chat 测试报告</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .summary {{ padding: 12px; background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #d0d7de; padding: 8px; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
  </style>
</head>
<body>
  <h1>知识库聊天 pytest 报告</h1>
  <div class='summary'>
    <div><strong>生成时间:</strong> {_esc(str(meta.get('generated_at', '')))}</div>
    <div><strong>总测试数:</strong> {_esc(str(meta.get('total_tests', 0)))} | <strong>通过:</strong> {_esc(str(meta.get('passed_tests', 0)))} | <strong>失败:</strong> {_esc(str(meta.get('failed_tests', 0)))} | <strong>通过率:</strong> {_esc(f"{meta.get('pass_rate', 0):.2f}%")}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>用例</th>
        <th>问题</th>
        <th>结果</th>
        <th>耗时(s)</th>
        <th>检索证据</th>
        <th>回答</th>
        <th>缺失元素</th>
        <th>禁用元素</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _md_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", "<br>")
