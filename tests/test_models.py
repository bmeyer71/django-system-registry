from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from system_resgistry.models import SystemSetting


@pytest.mark.django_db
class TestSystemSettingModel:
    def test_get_value_falls_back_to_registry(self) -> None:
        assert SystemSetting.get_value("api", "page_size") == 20

    def test_set_value_creates_typed_int_setting(self) -> None:
        setting = SystemSetting.set_value("api", "page_size", "50")
        assert setting.value == "50"
        assert setting.typed_value == 50

    def test_set_value_serializes_list_as_json(self) -> None:
        setting = SystemSetting.set_value("notifications", "channels", ["email", "sms"])
        assert setting.value == '["email", "sms"]'
        assert setting.typed_value == ["email", "sms"]

    def test_set_value_serializes_dict_as_json(self) -> None:
        setting = SystemSetting.set_value("ui", "theme_config", {"default": "dark"})
        assert setting.value == '{"default": "dark"}'
        assert setting.typed_value == {"default": "dark"}

    def test_set_value_uses_definition_description(self) -> None:
        setting = SystemSetting.set_value("features", "signup_enabled", True)
        assert setting.description == "Allow self-service signup."

    def test_get_value_prefers_database_override(self) -> None:
        SystemSetting.set_value("api", "page_size", 30)
        assert SystemSetting.get_value("api", "page_size") == 30

    def test_get_value_uses_fallback_for_unregistered_setting(self) -> None:
        assert SystemSetting.get_value("missing", "key", default="fallback") == "fallback"

    def test_get_namespace_settings_merges_defaults_and_overrides(self) -> None:
        SystemSetting.set_value("billing", "trial_days", 21)
        settings = SystemSetting.get_namespace_settings("billing")
        assert settings == {
            "plan_code": "starter",
            "trial_days": 21,
        }

    def test_sync_with_registry_creates_missing_settings(self) -> None:
        result = SystemSetting.sync_with_registry()
        assert result == {"created": 6, "updated": 0, "existing": 0}
        assert SystemSetting.objects.count() == 6

    def test_sync_with_registry_updates_changed_descriptions(self) -> None:
        SystemSetting.objects.create(
            namespace="api",
            key="page_size",
            value="20",
            description="Old description",
        )
        result = SystemSetting.sync_with_registry(namespace="api")
        assert result == {"created": 0, "updated": 1, "existing": 0}
        assert (
            SystemSetting.objects.get(namespace="api", key="page_size").description
            == "Default page size."
        )

    def test_clean_rejects_unregistered_setting(self) -> None:
        setting = SystemSetting(namespace="missing", key="key", value="value")
        with pytest.raises(ValidationError, match="not registered"):
            setting.full_clean()

    def test_clean_rejects_invalid_value(self) -> None:
        setting = SystemSetting(namespace="api", key="page_size", value="200")
        with pytest.raises(ValidationError, match="above maximum"):
            setting.full_clean()
