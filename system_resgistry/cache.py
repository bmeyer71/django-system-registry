from __future__ import annotations

from django.core.cache import cache

from system_resgistry.conf import get_cache_prefix


def get_cache_key(namespace: str, key: str) -> str:
    return f"{get_cache_prefix()}{namespace}.{key}"


def invalidate_cache_key(namespace: str, key: str) -> None:
    cache.delete(get_cache_key(namespace, key))
