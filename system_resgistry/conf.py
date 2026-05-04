from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

RegistryDefinitions = dict[tuple[str, str], dict[str, Any]]
DefinitionsProvider = Callable[[], RegistryDefinitions]

DEFAULT_CACHE_PREFIX = "system_resgistry:"
DEFAULT_CACHE_TIMEOUT = 300


def get_registry_definitions() -> RegistryDefinitions:
    definitions: RegistryDefinitions = {}

    provider = getattr(settings, "SYSTEM_RESGISTRY_DEFINITIONS_PROVIDER", None)
    if provider is not None:
        loader = _coerce_provider(provider)
        definitions.update(loader())

    definitions.update(getattr(settings, "SYSTEM_RESGISTRY_DEFINITIONS", {}))
    return definitions


def get_cache_prefix() -> str:
    return str(getattr(settings, "SYSTEM_RESGISTRY_CACHE_PREFIX", DEFAULT_CACHE_PREFIX))


def get_cache_timeout() -> int:
    return int(getattr(settings, "SYSTEM_RESGISTRY_CACHE_TIMEOUT", DEFAULT_CACHE_TIMEOUT))


def _coerce_provider(provider: str | DefinitionsProvider) -> DefinitionsProvider:
    loaded = import_string(provider) if isinstance(provider, str) else provider

    if not callable(loaded):
        msg = "SYSTEM_RESGISTRY_DEFINITIONS_PROVIDER must be callable."
        raise TypeError(msg)

    return loaded
