from __future__ import annotations

import os
from typing import Any

import pytest

from .kb_chat_reporting import write_reports


def _env_flag(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def pytest_configure(config: pytest.Config) -> None:
    # Store results on config so both fixtures and hooks can access.
    config._kb_chat_results = []  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def kb_chat_results(request: pytest.FixtureRequest) -> list[dict[str, Any]]:
    return request.config._kb_chat_results  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _env_flag("KB_CHAT_GENERATE_REPORT", default=False):
        return

    results = getattr(session.config, "_kb_chat_results", [])
    if not results:
        return

    paths = write_reports(results)
    print(f"\n[KB_CHAT_GENERATE_REPORT] wrote: {paths.json_path}")
    print(f"[KB_CHAT_GENERATE_REPORT] wrote: {paths.html_path}\n")
