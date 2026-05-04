from __future__ import annotations

from typing import Any

from django.core.cache import cache

from system_resgistry.cache import get_cache_key
from system_resgistry.conf import get_cache_timeout
from system_resgistry.models import SystemSetting
from system_resgistry.registry import SettingsRegistry

_CACHE_MISS = object()


class SettingsService:
    """Cache-aware reads and writes for registry-backed settings."""

    @classmethod
    def _cache_key(cls, namespace: str, key: str) -> str:
        return get_cache_key(namespace, key)

    @classmethod
    def _cache_timeout(cls) -> int:
        return get_cache_timeout()

    @classmethod
    def get_setting(cls, namespace: str, key: str, default: Any = None) -> Any:
        cache_key = cls._cache_key(namespace, key)
        cached_value = cache.get(cache_key, _CACHE_MISS)
        if cached_value is not _CACHE_MISS:
            return cached_value

        value = SystemSetting.get_value(namespace, key, default=default)
        cache.set(cache_key, value, cls._cache_timeout())
        return value

    @classmethod
    def set_setting(
        cls,
        namespace: str,
        key: str,
        value: Any,
        description: str | None = None,
    ) -> SystemSetting:
        setting = SystemSetting.set_value(namespace, key, value, description=description)
        cache.set(cls._cache_key(namespace, key), setting.typed_value, cls._cache_timeout())
        return setting

    @classmethod
    def delete_setting(cls, namespace: str, key: str) -> bool:
        cache.delete(cls._cache_key(namespace, key))
        deleted, _ = SystemSetting.objects.filter(namespace=namespace, key=key).delete()
        return deleted > 0

    @classmethod
    def clear_cache(cls, namespace: str | None = None, key: str | None = None) -> None:
        if namespace is not None and key is not None:
            cache.delete(cls._cache_key(namespace, key))
            return

        keys_to_clear: set[str] = set()

        if namespace is not None:
            keys_to_clear.update(
                cls._cache_key(namespace, registered_key)
                for registered_key in SettingsRegistry.get_settings_by_namespace(namespace)
            )
            keys_to_clear.update(
                cls._cache_key(namespace, registered_key)
                for registered_key in SystemSetting.objects.filter(
                    namespace=namespace
                ).values_list("key", flat=True)
            )
        else:
            keys_to_clear.update(
                cls._cache_key(registered_namespace, registered_key)
                for registered_namespace, registered_key in SettingsRegistry.all_definitions()
            )
            keys_to_clear.update(
                cls._cache_key(registered_namespace, registered_key)
                for registered_namespace, registered_key in SystemSetting.objects.values_list(
                    "namespace", "key"
                )
            )

        if keys_to_clear:
            cache.delete_many(list(keys_to_clear))


def get_system_setting(namespace: str, key: str, default: Any = None) -> Any:
    return SettingsService.get_setting(namespace, key, default=default)


def set_system_setting(
    namespace: str,
    key: str,
    value: Any,
    description: str | None = None,
) -> SystemSetting:
    return SettingsService.set_setting(namespace, key, value, description=description)


def sync_system_settings(namespace: str | None = None) -> dict[str, int]:
    return SystemSetting.sync_with_registry(namespace=namespace)
