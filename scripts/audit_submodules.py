from __future__ import annotations

import argparse
import html
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


SUBMODULES = ("frontend", "miniprogram")


@dataclass
class SubmoduleAudit:
    name: str
    path: str
    recorded_commit: str | None
    head_commit: str | None
    branch_line: str
    ahead: int
    behind: int
    dirty_entries: list[str]
    pointer_drift: bool
    status_symbol: str


def run_git(repo: Path, args: list[str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git -C {repo} {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.rstrip("\n")


def parse_ahead_behind(branch_line: str) -> tuple[int, int]:
    ahead = 0
    behind = 0
    marker_start = branch_line.find("[")
    marker_end = branch_line.find("]", marker_start + 1)
    if marker_start == -1 or marker_end == -1:
        return ahead, behind
    marker = branch_line[marker_start + 1 : marker_end]
    for chunk in marker.split(","):
        part = chunk.strip()
        if part.startswith("ahead "):
            ahead = int(part.split(" ", 1)[1])
        elif part.startswith("behind "):
            behind = int(part.split(" ", 1)[1])
    return ahead, behind


def parent_gitlinks(repo: Path) -> dict[str, str]:
    output = run_git(repo, ["ls-files", "-s", *SUBMODULES])
    links: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "160000":
            links[parts[3]] = parts[1]
    return links


def submodule_status_symbols(repo: Path) -> dict[str, str]:
    output = run_git(repo, ["submodule", "status", "--recursive"])
    symbols: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            continue
        symbol = line[0]
        fields = line[1:].split()
        if len(fields) >= 2:
            symbols[fields[1]] = symbol
    return symbols


def audit(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    links = parent_gitlinks(repo)
    symbols = submodule_status_symbols(repo)
    parent_status = run_git(repo, ["status", "--short", "--ignore-submodules=none"])

    modules: list[SubmoduleAudit] = []
    for name in SUBMODULES:
        sub_path = repo / name
        status_lines = run_git(sub_path, ["status", "--short", "--branch"]).splitlines()
        branch_line = status_lines[0] if status_lines else ""
        dirty_entries = status_lines[1:]
        ahead, behind = parse_ahead_behind(branch_line)
        head = run_git(sub_path, ["rev-parse", "HEAD"])
        recorded = links.get(name)
        modules.append(
            SubmoduleAudit(
                name=name,
                path=str(sub_path),
                recorded_commit=recorded,
                head_commit=head,
                branch_line=branch_line,
                ahead=ahead,
                behind=behind,
                dirty_entries=dirty_entries,
                pointer_drift=bool(recorded and head and recorded != head),
                status_symbol=symbols.get(name, " "),
            )
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo": str(repo),
        "parent_status": parent_status.splitlines(),
        "modules": [asdict(module) for module in modules],
        "next_steps": [
            "Review each child repository diff and ahead commits inside the submodule.",
            "Commit and push child repository changes before updating parent gitlinks.",
            "Return to the parent repository and commit only intentional gitlink pointer updates.",
        ],
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "submodule_audit_REPORT.json"
    md_path = out_dir / "submodule_audit_REPORT.md"
    html_path = out_dir / "submodule_audit_REPORT.html"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")
    html_path.write_text(to_html(report), encoding="utf-8")
    return {"json": json_path, "md": md_path, "html": html_path}


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Submodule Audit Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Parent repo: `{report['repo']}`",
        "",
        "## Parent Status",
        "",
    ]
    parent_status = report.get("parent_status") or []
    if parent_status:
        lines.extend(f"- `{line}`" for line in parent_status)
    else:
        lines.append("- Clean")

    lines.extend(
        [
            "",
            "## Submodules",
            "",
            "| Name | Recorded Commit | HEAD | Ahead | Behind | Dirty | Pointer Drift | Status Symbol |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for module in report["modules"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    module["name"],
                    short(module.get("recorded_commit")),
                    short(module.get("head_commit")),
                    str(module["ahead"]),
                    str(module["behind"]),
                    str(len(module["dirty_entries"])),
                    "yes" if module["pointer_drift"] else "no",
                    md_cell(module["status_symbol"] or " "),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Dirty Entries", ""])
    for module in report["modules"]:
        lines.append(f"### {module['name']}")
        entries = module["dirty_entries"]
        if entries:
            lines.extend(f"- `{entry}`" for entry in entries)
        else:
            lines.append("- Clean worktree")
        lines.append("")

    lines.extend(["## Recommended Order", ""])
    lines.extend(f"{i}. {step}" for i, step in enumerate(report["next_steps"], start=1))
    lines.append("")
    return "\n".join(lines)


def to_html(report: dict[str, Any]) -> str:
    rows = []
    for module in report["modules"]:
        rows.append(
            "<tr>"
            f"<td>{esc(module['name'])}</td>"
            f"<td><code>{esc(short(module.get('recorded_commit')))}</code></td>"
            f"<td><code>{esc(short(module.get('head_commit')))}</code></td>"
            f"<td>{module['ahead']}</td>"
            f"<td>{module['behind']}</td>"
            f"<td>{len(module['dirty_entries'])}</td>"
            f"<td>{'yes' if module['pointer_drift'] else 'no'}</td>"
            f"<td>{esc(module['status_symbol'] or ' ')}</td>"
            "</tr>"
        )
    parent_items = "".join(f"<li><code>{esc(line)}</code></li>" for line in report.get("parent_status") or ["Clean"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Submodule Audit Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 28px; color: #172033; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #d9e2ef; padding: 8px; vertical-align: top; }}
    th {{ background: #f4f7fb; text-align: left; }}
    code {{ background: #f4f7fb; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Submodule Audit Report</h1>
  <p><strong>Generated at:</strong> {esc(report['generated_at'])}</p>
  <p><strong>Parent repo:</strong> <code>{esc(report['repo'])}</code></p>
  <h2>Parent Status</h2>
  <ul>{parent_items}</ul>
  <h2>Submodules</h2>
  <table>
    <thead>
      <tr><th>Name</th><th>Recorded</th><th>HEAD</th><th>Ahead</th><th>Behind</th><th>Dirty</th><th>Pointer Drift</th><th>Symbol</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Recommended Order</h2>
  <ol>{''.join(f'<li>{esc(step)}</li>' for step in report['next_steps'])}</ol>
</body>
</html>
"""


def short(value: str | None) -> str:
    if not value:
        return ""
    return value[:7]


def md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="parent repository path")
    parser.add_argument("--out-dir", default="reports", help="report output directory")
    args = parser.parse_args()
    report = audit(Path(args.repo))
    paths = write_outputs(report, Path(args.out_dir))
    for kind, path in paths.items():
        print(f"wrote {kind}: {path}")


if __name__ == "__main__":
    main()
