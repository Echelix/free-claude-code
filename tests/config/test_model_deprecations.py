"""Echelix: deprecated NVIDIA NIM model refs self-heal in managed config."""

import pytest

from free_claude_code.config.env_files import dotenv_values_from_file
from free_claude_code.config.env_migrations import consolidate_managed_config
from free_claude_code.config.model_refs import (
    DEPRECATED_NVIDIA_NIM_MODELS,
    normalize_retired_model_settings,
    replace_deprecated_model_ref,
)

OLD = "nvidia_nim/moonshotai/kimi-k2-thinking"
NEW = DEPRECATED_NVIDIA_NIM_MODELS[OLD]


def test_deprecation_map_targets_are_not_themselves_deprecated() -> None:
    for old, new in DEPRECATED_NVIDIA_NIM_MODELS.items():
        assert old.startswith("nvidia_nim/")
        assert new.startswith("nvidia_nim/")
        assert new not in DEPRECATED_NVIDIA_NIM_MODELS


@pytest.mark.parametrize("ref", ["nvidia_nim/qwen/qwen3.5-397b-a17b", "groq/a", ""])
def test_replace_deprecated_model_ref_leaves_current_refs_alone(ref: str) -> None:
    assert replace_deprecated_model_ref(ref) == ref


def test_replace_deprecated_model_ref_tolerates_surrounding_whitespace() -> None:
    assert replace_deprecated_model_ref(f"  {OLD} ") == NEW


@pytest.mark.parametrize("preserve_empty_overrides", [True, False])
def test_normalize_replaces_deprecated_route_and_fallback_refs(
    preserve_empty_overrides: bool,
) -> None:
    values = {
        "MODEL": OLD,
        "MODEL_SONNET": "nvidia_nim/qwen/qwen3.5-397b-a17b",
        "MODEL_HAIKU": "nvidia_nim/moonshotai/kimi-k2-instruct",
        "MODEL_FALLBACKS": f"groq/a,{OLD},deepseek/b",
        "UNRELATED": "kept",
    }

    normalized = normalize_retired_model_settings(
        values, preserve_empty_overrides=preserve_empty_overrides
    )

    assert normalized["MODEL"] == NEW
    assert normalized["MODEL_SONNET"] == "nvidia_nim/qwen/qwen3.5-397b-a17b"
    assert normalized["MODEL_HAIKU"] == "nvidia_nim/qwen/qwen3.5-122b-a10b"
    assert normalized["MODEL_FALLBACKS"] == f"groq/a,{NEW},deepseek/b"
    assert normalized["UNRELATED"] == "kept"
    assert values["MODEL"] == OLD, "input mapping must not be mutated"


def test_normalize_is_a_no_op_without_deprecated_refs() -> None:
    values = {"MODEL": NEW, "MODEL_FALLBACKS": "groq/a,deepseek/b"}

    assert normalize_retired_model_settings(values, preserve_empty_overrides=False) == (
        values
    )


def test_startup_consolidation_rewrites_deprecated_models_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("FCC_ENV_FILE", raising=False)
    managed = tmp_path / ".fcc" / ".env"
    managed.parent.mkdir(parents=True)
    managed.write_text(
        f"FCC_CONFIG_SCHEMA=1\nMODEL={OLD}\nMODEL_OPUS={OLD}\nNVIDIA_NIM_API_KEY=secret\n",
        encoding="utf-8",
    )

    assert consolidate_managed_config({}).changed
    values = dotenv_values_from_file(managed)
    assert values["MODEL"] == NEW
    assert values["MODEL_OPUS"] == NEW
    assert values["NVIDIA_NIM_API_KEY"] == "secret"

    before = managed.read_bytes()
    assert not consolidate_managed_config({}).changed
    assert managed.read_bytes() == before
