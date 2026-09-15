"""Echelix ``fcc-models``: verify configured model refs against live provider catalogs.

Providers retire models without notice (NVIDIA NIM answers HTTP 410 once a model
reaches end of life). This command reads the managed configuration, asks every
configured cloud provider for its current ``/models`` list, and reports each
``MODEL*`` reference as live, missing, or unverified. It exits non-zero when any
reference is missing so it can gate scripts and CI.
"""

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

import httpx

from free_claude_code.config.loader import get_settings
from free_claude_code.config.model_refs import (
    DEPRECATED_NVIDIA_NIM_MODELS,
    configured_chat_model_refs,
)
from free_claude_code.config.provider_catalog import PROVIDER_CATALOG
from free_claude_code.config.settings import Settings

MODELS_TIMEOUT_SECONDS = 15.0

CheckStatus = Literal["live", "missing", "unverified"]
ModelIdFetcher = Callable[[str, Settings], frozenset[str] | None]


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """Outcome for one configured ``provider/model`` reference."""

    model_ref: str
    provider_id: str
    status: CheckStatus
    detail: str = ""

    @property
    def suggestion(self) -> str | None:
        return DEPRECATED_NVIDIA_NIM_MODELS.get(self.model_ref)


def _model_ids_from_payload(payload: object) -> frozenset[str]:
    entries = payload.get("data") if isinstance(payload, Mapping) else payload
    if not isinstance(entries, list):
        raise ValueError("models payload has no list of entries")
    return frozenset(
        entry["id"]
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    )


def _http_client(proxy: str | None) -> httpx.Client:
    return httpx.Client(timeout=MODELS_TIMEOUT_SECONDS, proxy=proxy)


def fetch_provider_model_ids(
    provider_id: str, settings: Settings
) -> frozenset[str] | None:
    """Return a provider's live model ids, or ``None`` when it cannot be listed."""

    descriptor = PROVIDER_CATALOG.get(provider_id)
    if descriptor is None or descriptor.local:
        return None
    base_url: str | None = None
    if descriptor.base_url_attr:
        base_url = getattr(settings, descriptor.base_url_attr, None)
    base_url = base_url or descriptor.default_base_url
    if not base_url:
        return None

    headers: dict[str, str] = {}
    if descriptor.credential_attr:
        credential = getattr(settings, descriptor.credential_attr, None)
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
    proxy: str | None = None
    if descriptor.proxy_attr:
        proxy = getattr(settings, descriptor.proxy_attr, None) or None

    try:
        with _http_client(proxy) as client:
            response = client.get(f"{base_url.rstrip('/')}/models", headers=headers)
            response.raise_for_status()
            return _model_ids_from_payload(response.json())
    except httpx.HTTPError, ValueError, KeyError, TypeError:
        return None


def check_configured_models(
    settings: Settings, fetch: ModelIdFetcher = fetch_provider_model_ids
) -> list[ModelCheck]:
    """Check every configured chat model ref against its provider's live list."""

    catalogs: dict[str, frozenset[str] | None] = {}
    checks: list[ModelCheck] = []
    for ref in configured_chat_model_refs(settings):
        if ref.provider_id not in catalogs:
            catalogs[ref.provider_id] = fetch(ref.provider_id, settings)
        live_ids = catalogs[ref.provider_id]
        if live_ids is None:
            checks.append(
                ModelCheck(
                    ref.model_ref,
                    ref.provider_id,
                    "unverified",
                    "provider model list unavailable",
                )
            )
        elif ref.model_id in live_ids:
            checks.append(ModelCheck(ref.model_ref, ref.provider_id, "live"))
        else:
            checks.append(
                ModelCheck(
                    ref.model_ref,
                    ref.provider_id,
                    "missing",
                    "not in the provider's current model list",
                )
            )
    return checks


def format_report(checks: list[ModelCheck]) -> str:
    width = max((len(check.model_ref) for check in checks), default=0)
    lines = [
        f"{check.model_ref.ljust(width)}  {check.status.upper():<10} {check.detail}".rstrip()
        for check in checks
    ]
    lines.extend(
        f"  → replace {check.model_ref} with {replacement}"
        for check in checks
        if check.status == "missing" and (replacement := check.suggestion)
    )
    missing = sum(check.status == "missing" for check in checks)
    if missing:
        lines.append(
            f"{missing} configured model(s) are no longer served. Update MODEL* in "
            "~/.fcc/.env or Admin → Model Config, then restart (fcc-stop && fcc-start)."
        )
    else:
        lines.append("All configured models are served by their providers.")
    return "\n".join(lines)


def fcc_models() -> None:
    """Report configured model availability (registered as ``fcc-models``)."""

    checks = check_configured_models(get_settings())
    print(format_report(checks))
    if any(check.status == "missing" for check in checks):
        sys.exit(1)
