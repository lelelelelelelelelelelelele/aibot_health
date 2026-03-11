from __future__ import annotations

import httpx
import pytest

from tests.model_connectivity_support import build_connectivity_cases, call_cloud_chat_api, validate_connectivity_result


@pytest.mark.parametrize(("provider_group", "model"), build_connectivity_cases())
def test_cloud_model_connectivity(provider_group: str, model: str) -> None:
    try:
        result = call_cloud_chat_api(model)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
        pytest.fail(f"Cloud endpoint unreachable for {provider_group}/{model}: {exc!r}")

    validation_error = validate_connectivity_result(result)
    response_summary = str(result.get("response"))[:500]
    raw_summary = str(result.get("raw_text", ""))[:500]

    assert validation_error is None, (
        f"{provider_group}/{model} connectivity failed: {validation_error}\n"
        f"status_code={result.get('status_code')}\n"
        f"extracted_content={result.get('extracted_content')!r}\n"
        f"error_message={result.get('error_message')!r}\n"
        f"response={response_summary}\n"
        f"raw_text={raw_summary}"
    )
