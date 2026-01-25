from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ReportPaths:
    json_path: Path
    html_path: Path


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_reports(results: list[dict[str, Any]], output_dir: str | Path = "test_reports") -> ReportPaths:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    json_path = out_dir / f"kb_chat_test_report_{ts}.json"
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
    html_path.write_text(_to_html(report), encoding="utf-8")

    return ReportPaths(json_path=json_path, html_path=html_path)


def _to_html(report: dict[str, Any]) -> str:
    meta = report.get("report_metadata", {})
    rows = []
    for i, r in enumerate(report.get("test_results", []), start=1):
        ok = bool(r.get("ok"))
        status = "通过" if ok else "失败"
        rows.append(
            "".join(
                [
                    f"<tr>",
                    f"<td>{i}</td>",
                    f"<td>{_esc(str(r.get('test_name', '')))}</td>",
                    f"<td>{_esc(str(r.get('question', '')))}</td>",
                    f"<td>{status}</td>",
                    f"<td>{_esc(str(r.get('elapsed_s', '')))}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(str(r.get('answer', '')))}</td>",
                    f"<td style='white-space:pre-wrap'>{_esc(json.dumps(r.get('missing', []), ensure_ascii=False))}</td>",
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
        <th>回答</th>
        <th>缺失元素</th>
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
