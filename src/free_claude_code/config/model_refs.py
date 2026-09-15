"""Provider-prefixed model reference helpers."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .constants import DEFAULT_MODEL

RETIRED_PROVIDER_IDS = frozenset({"github_models"})

# Echelix: deprecated NVIDIA NIM model refs and their drop-in replacements.
# Keys are complete ``provider/org/name`` refs. Add an entry whenever NIM retires a
# model so managed config self-heals instead of failing startup model validation.
# Verify the live list with ``fcc-models`` (or GET {NIM base}/models) before editing.
DEPRECATED_NVIDIA_NIM_MODELS: dict[str, str] = {
    # Kimi K2 family retired (2026-05)
    "nvidia_nim/moonshotai/kimi-k2-thinking": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
    "nvidia_nim/moonshotai/kimi-k2-instruct": "nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b",
    # Qwen family reached end of life on NIM (2026-07-27)
    "nvidia_nim/qwen/qwen3-next-80b-a3b-thinking": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
    "nvidia_nim/qwen/qwen3.5-397b-a17b": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
    "nvidia_nim/qwen/qwen3.5-122b-a10b": "nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b",
    # GLM 4.7 / GLM 5 replaced by GLM 5.3 Flash
    "nvidia_nim/z-ai/glm4.7": "nvidia_nim/z-ai/glm-5.3-flash",
    "nvidia_nim/z-ai/glm5": "nvidia_nim/z-ai/glm-5.3-flash",
}
_MODEL_ROUTE_KEYS = (
    "MODEL",
    "MODEL_FABLE",
    "MODEL_OPUS",
    "MODEL_SONNET",
    "MODEL_HAIKU",
)


def is_retired_model_ref(model_ref: str) -> bool:
    """Recognize complete references owned by a retired provider."""

    provider, separator, model = model_ref.strip().partition("/")
    return provider in RETIRED_PROVIDER_IDS and bool(separator and model.strip())


def parse_model_fallbacks(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        return tuple(part.strip() for part in value.split(","))
    if isinstance(value, list | tuple) and not value:
        return None
    return value


def replace_deprecated_model_ref(model_ref: str) -> str:
    """Return the replacement for a deprecated NVIDIA NIM ref, else the ref unchanged."""

    return DEPRECATED_NVIDIA_NIM_MODELS.get(model_ref.strip(), model_ref)


def normalize_retired_model_settings(
    values: Mapping[str, str], *, preserve_empty_overrides: bool
) -> dict[str, str]:
    """Repair one source without changing its precedence or unrelated validation."""

    normalized = dict(values)
    for key in _MODEL_ROUTE_KEYS:
        current = normalized.get(key, "")
        replacement = replace_deprecated_model_ref(current)
        if replacement != current:
            normalized[key] = replacement
        if is_retired_model_ref(normalized.get(key, "")):
            if preserve_empty_overrides:
                normalized[key] = DEFAULT_MODEL if key == "MODEL" else ""
            else:
                normalized.pop(key)
    fallbacks = parse_model_fallbacks(normalized.get("MODEL_FALLBACKS"))
    if isinstance(fallbacks, tuple) and all(fallbacks):
        replaced = tuple(replace_deprecated_model_ref(ref) for ref in fallbacks)
        retained = tuple(ref for ref in replaced if not is_retired_model_ref(ref))
        if retained != fallbacks:
            if retained or preserve_empty_overrides:
                normalized["MODEL_FALLBACKS"] = ",".join(retained)
            else:
                normalized.pop("MODEL_FALLBACKS")
    return normalized


@dataclass(frozen=True, slots=True)
class ConfiguredChatModelRef:
    """A unique configured chat model reference."""

    model_ref: str
    provider_id: str
    model_id: str


class ChatModelConfig(Protocol):
    model: str
    model_fable: str | None
    model_opus: str | None
    model_sonnet: str | None
    model_haiku: str | None
    model_fallbacks: tuple[str, ...] | None


def split_provider_model_ref(model_ref: str) -> tuple[str, str]:
    """Split one complete ``provider/model`` reference."""

    provider_id, separator, model_id = model_ref.partition("/")
    if not separator or not provider_id or not model_id:
        raise ValueError("Model reference must contain provider and model names.")
    return provider_id, model_id


def parse_provider_type(model_ref: str) -> str:
    """Extract provider type from any 'provider/model' string."""

    return split_provider_model_ref(model_ref)[0]


def parse_model_name(model_ref: str) -> str:
    """Extract model name from any 'provider/model' string."""

    return split_provider_model_ref(model_ref)[1]


def configured_chat_model_refs(
    settings: ChatModelConfig,
) -> tuple[ConfiguredChatModelRef, ...]:
    """Return unique configured chat provider/model refs."""

    model_refs = dict.fromkeys(
        model_ref
        for model_ref in (
            settings.model,
            settings.model_fable,
            settings.model_opus,
            settings.model_sonnet,
            settings.model_haiku,
            *(settings.model_fallbacks or ()),
        )
        if model_ref is not None
    )

    return tuple(
        ConfiguredChatModelRef(
            model_ref=model_ref,
            provider_id=parse_provider_type(model_ref),
            model_id=parse_model_name(model_ref),
        )
        for model_ref in model_refs
    )
