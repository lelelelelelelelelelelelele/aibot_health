#!/usr/bin/env python3
"""Create a transferable bundle of the `data1/` folder.

Goals:
- Keep KB data (content, vector_store, sqlite DB if present)
- Exclude noisy/ephemeral folders (logs, temp, __pycache__)
- Redact obvious API keys from YAML files in the bundle

Usage:
  python scripts/package_data1_bundle.py --src data1 --out data1_bundle.tgz

Notes:
- This script *does not* modify your original `data1/`.
- It redacts patterns like `api_key: sk-...` inside *.yml/*.yaml files.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDES = [
    "data/logs",
    "data/temp",
    "**/__pycache__",
]


@dataclass(frozen=True)
class Stats:
    files_copied: int = 0
    bytes_copied: int = 0
    yaml_files_scanned: int = 0
    yaml_files_redacted: int = 0
    redactions: int = 0


def _norm_rel(path: Path) -> str:
    return path.as_posix().lstrip("./")


def _is_excluded(rel_posix: str, patterns: Iterable[str]) -> bool:
    rel_posix = rel_posix.lstrip("./")
    for pattern in patterns:
        pattern = pattern.replace(os.sep, "/")
        if fnmatch.fnmatch(rel_posix, pattern) or rel_posix.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def copy_tree(src: Path, dst: Path, excludes: list[str]) -> Stats:
    stats = Stats()
    src = src.resolve()
    dst = dst.resolve()

    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel_root = _norm_rel(root_path.relative_to(src))

        # Prune excluded directories
        pruned_dirs: list[str] = []
        for d in list(dirs):
            rel_dir = _norm_rel(Path(rel_root) / d)
            if _is_excluded(rel_dir, excludes):
                pruned_dirs.append(d)
        for d in pruned_dirs:
            dirs.remove(d)

        target_root = dst / rel_root
        target_root.mkdir(parents=True, exist_ok=True)

        for filename in files:
            rel_file = _norm_rel(Path(rel_root) / filename)
            if _is_excluded(rel_file, excludes):
                continue
            src_file = root_path / filename
            dst_file = target_root / filename
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            try:
                size = src_file.stat().st_size
            except OSError:
                size = 0
            stats = Stats(
                files_copied=stats.files_copied + 1,
                bytes_copied=stats.bytes_copied + size,
                yaml_files_scanned=stats.yaml_files_scanned,
                yaml_files_redacted=stats.yaml_files_redacted,
                redactions=stats.redactions,
            )

    return stats


API_KEY_RE = re.compile(r"^(\s*api_key\s*:\s*)([^#\n\r]+)", re.IGNORECASE | re.MULTILINE)
SK_LIKE_RE = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")


def redact_yaml_secrets(root: Path) -> Stats:
    stats = Stats()

    for path in root.rglob("*.yml"):
        stats = _redact_one_yaml(path, stats)
    for path in root.rglob("*.yaml"):
        stats = _redact_one_yaml(path, stats)

    return stats


def _redact_one_yaml(path: Path, stats: Stats) -> Stats:
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        original = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return stats

    stats = Stats(
        files_copied=stats.files_copied,
        bytes_copied=stats.bytes_copied,
        yaml_files_scanned=stats.yaml_files_scanned + 1,
        yaml_files_redacted=stats.yaml_files_redacted,
        redactions=stats.redactions,
    )

    redactions = 0

    def repl_api_key(match: re.Match[str]) -> str:
        nonlocal redactions
        prefix = match.group(1)
        value = match.group(2).strip()
        # Only redact non-empty values; keep '' and ${ENV} style placeholders.
        if value in {"''", '""', "", "null", "None"}:
            return match.group(0)
        if value.startswith("${") and value.endswith("}"):
            return match.group(0)
        # If it looks like a real key/token, redact.
        if "sk-" in value or len(value) >= 12:
            redactions += 1
            return f"{prefix}''  # REDACTED"
        return match.group(0)

    updated = API_KEY_RE.sub(repl_api_key, original)

    # Extra safety: replace any stray sk-... tokens (e.g. inside URLs/comments)
    def repl_sk(m: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return "sk-REDACTED"

    updated2 = SK_LIKE_RE.sub(repl_sk, updated)

    if updated2 != original:
        try:
            path.write_text(updated2, encoding="utf-8")
        except OSError:
            return stats
        stats = Stats(
            files_copied=stats.files_copied,
            bytes_copied=stats.bytes_copied,
            yaml_files_scanned=stats.yaml_files_scanned,
            yaml_files_redacted=stats.yaml_files_redacted + 1,
            redactions=stats.redactions + redactions,
        )

    return stats


def make_tar_gz(src_dir: Path, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out_file, "w:gz") as tf:
        tf.add(src_dir, arcname=src_dir.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe transfer bundle of data1/")
    parser.add_argument("--src", default="data1", help="Source directory to bundle (default: data1)")
    parser.add_argument(
        "--out",
        default=None,
        help="Output .tgz path (default: <src>_bundle.tgz next to repo root)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude pattern (can be repeated). Examples: data/logs, **/__pycache__",
    )

    args = parser.parse_args()

    repo_root = Path.cwd()
    src = (repo_root / args.src).resolve()
    if not src.exists() or not src.is_dir():
        raise SystemExit(f"Source directory not found: {src}")

    out = Path(args.out) if args.out else (repo_root / f"{src.name}_bundle.tgz")
    excludes = DEFAULT_EXCLUDES + list(args.exclude or [])

    with tempfile.TemporaryDirectory(prefix=f"{src.name}_bundle_") as tmp:
        staging_root = Path(tmp) / src.name
        copy_stats = copy_tree(src, staging_root, excludes=excludes)
        redact_stats = redact_yaml_secrets(staging_root)
        make_tar_gz(staging_root, out)

    print(f"Wrote bundle: {out}")
    print(f"Copied: {copy_stats.files_copied} files, {copy_stats.bytes_copied / (1024 * 1024):.2f} MiB")
    print(
        "Redaction: "
        f"scanned {redact_stats.yaml_files_scanned} yaml files, "
        f"modified {redact_stats.yaml_files_redacted}, "
        f"redactions {redact_stats.redactions}"
    )
    print(f"Excluded patterns: {', '.join(excludes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
