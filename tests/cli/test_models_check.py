"""Echelix fcc-models: configured model refs vs live provider catalogs."""

import json

import httpx
import pytest

from free_claude_code.cli import models_check
from free_claude_code.cli.models_check import (
    ModelCheck,
    check_configured_models,
    fetch_provider_model_ids,
    format_report,
)
from free_claude_code.config.model_refs import DEPRECATED_NVIDIA_NIM_MODELS
from free_claude_code.config.settings import Settings

RETIRED = "nvidia_nim/qwen/qwen3.5-397b-a17b"
LIVE = "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "model": LIVE,
        "model_sonnet": RETIRED,
        "model_haiku": "groq/llama-3.3-70b-versatile",
        "nvidia_nim_api_key": "nvapi-test",
        "groq_api_key": "gsk-test",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_check_reports_live_missing_and_unverified_per_provider() -> None:
    calls: list[str] = []

    def fetch(provider_id: str, settings: Settings) -> frozenset[str] | None:
        calls.append(provider_id)
        if provider_id == "nvidia_nim":
            return frozenset({"nvidia/nemotron-3-super-120b-a12b"})
        return None

    checks = check_configured_models(_settings(), fetch)

    assert [(c.model_ref, c.status) for c in checks] == [
        (LIVE, "live"),
        (RETIRED, "missing"),
        ("groq/llama-3.3-70b-versatile", "unverified"),
    ]
    assert calls == ["nvidia_nim", "groq"], "one catalog fetch per provider"


def test_missing_check_suggests_mapped_replacement() -> None:
    check = ModelCheck(RETIRED, "nvidia_nim", "missing")
    assert check.suggestion == DEPRECATED_NVIDIA_NIM_MODELS[RETIRED]
    assert ModelCheck(LIVE, "nvidia_nim", "live").suggestion is None


def test_format_report_lists_replacements_and_action() -> None:
    report = format_report(
        [
            ModelCheck(LIVE, "nvidia_nim", "live"),
            ModelCheck(RETIRED, "nvidia_nim", "missing", "not in list"),
        ]
    )

    assert "LIVE" in report and "MISSING" in report
    assert f"replace {RETIRED} with {DEPRECATED_NVIDIA_NIM_MODELS[RETIRED]}" in report
    assert "1 configured model(s) are no longer served" in report


def test_format_report_all_live() -> None:
    report = format_report([ModelCheck(LIVE, "nvidia_nim", "live")])
    assert report.endswith("All configured models are served by their providers.")


def test_fetch_uses_descriptor_base_url_and_bearer_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, json={"data": [{"id": "nvidia/nemotron-3-super-120b-a12b"}, {"id": 5}]}
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        models_check, "_http_client", lambda proxy: httpx.Client(transport=transport)
    )

    ids = fetch_provider_model_ids("nvidia_nim", _settings())

    assert ids == frozenset({"nvidia/nemotron-3-super-120b-a12b"})
    assert str(seen[0].url) == "https://integrate.api.nvidia.com/v1/models"
    assert seen[0].headers["authorization"] == "Bearer nvapi-test"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"error": "bad key"}),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json={"unexpected": True}),
    ],
)
def test_fetch_returns_none_when_provider_cannot_be_listed(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    transport = httpx.MockTransport(lambda request: response)
    monkeypatch.setattr(
        models_check, "_http_client", lambda proxy: httpx.Client(transport=transport)
    )

    assert fetch_provider_model_ids("nvidia_nim", _settings()) is None


def test_fetch_skips_local_and_unknown_providers() -> None:
    assert fetch_provider_model_ids("lmstudio", _settings()) is None
    assert fetch_provider_model_ids("no_such_provider", _settings()) is None


def test_fcc_models_exits_nonzero_when_a_model_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(models_check, "get_settings", _settings)
    monkeypatch.setattr(
        models_check,
        "fetch_provider_model_ids",
        lambda provider_id, settings: frozenset({"nvidia/nemotron-3-super-120b-a12b"}),
    )
    monkeypatch.setattr(
        models_check,
        "check_configured_models",
        lambda settings, fetch=None: check_configured_models(
            settings, models_check.fetch_provider_model_ids
        ),
    )

    with pytest.raises(SystemExit) as exc:
        models_check.fcc_models()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert RETIRED in out and "MISSING" in out
    json.dumps(out)  # plain text, no secrets or objects


def test_fcc_models_succeeds_when_all_live(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(
        models_check, "get_settings", lambda: _settings(model_sonnet=LIVE)
    )
    monkeypatch.setattr(
        models_check,
        "check_configured_models",
        lambda settings, fetch=None: [ModelCheck(LIVE, "nvidia_nim", "live")],
    )

    models_check.fcc_models()

    assert "All configured models are served" in capsys.readouterr().out
