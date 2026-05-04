from __future__ import annotations

import pytest
from django.core.cache import cache

from system_resgistry.models import SystemSetting
from system_resgistry.services import SettingsService, get_system_setting, set_system_setting


@pytest.mark.django_db
class TestSettingsService:
    def test_get_setting_uses_registry_default(self) -> None:
        assert SettingsService.get_setting("api", "page_size") == 20

    def test_get_setting_caches_result(self) -> None:
        value = SettingsService.get_setting("api", "page_size")
        cache_key = SettingsService._cache_key("api", "page_size")
        assert value == 20
        assert cache.get(cache_key) == 20

    def test_set_setting_updates_db_and_cache(self) -> None:
        setting = SettingsService.set_setting("features", "signup_enabled", True)
        assert setting.typed_value is True
        assert SystemSetting.get_value("features", "signup_enabled") is True
        assert cache.get(SettingsService._cache_key("features", "signup_enabled")) is True

    def test_delete_setting_clears_cache(self) -> None:
        SettingsService.set_setting("api", "page_size", 30)
        deleted = SettingsService.delete_setting("api", "page_size")
        assert deleted is True
        assert cache.get(SettingsService._cache_key("api", "page_size")) is None
        assert SystemSetting.get_value("api", "page_size") == 20

    def test_clear_cache_for_namespace(self) -> None:
        SettingsService.get_setting("billing", "trial_days")
        SettingsService.get_setting("billing", "plan_code")
        SettingsService.clear_cache(namespace="billing")
        assert cache.get(SettingsService._cache_key("billing", "trial_days")) is None
        assert cache.get(SettingsService._cache_key("billing", "plan_code")) is None

    def test_model_save_invalidates_cache(self) -> None:
        SettingsService.get_setting("api", "page_size")
        SystemSetting.set_value("api", "page_size", 60)
        assert cache.get(SettingsService._cache_key("api", "page_size")) is None

    def test_helpers_delegate_to_service(self) -> None:
        set_system_setting("billing", "trial_days", 10)
        assert get_system_setting("billing", "trial_days") == 10
