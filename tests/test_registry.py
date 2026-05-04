from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from system_resgistry.registry import SettingsRegistry


class TestSettingsRegistry:
    def test_get_definition_exists(self) -> None:
        definition = SettingsRegistry.get_definition("api", "page_size")
        assert definition is not None
        assert definition["type"] is int
        assert definition["default"] == 20

    def test_get_definition_missing(self) -> None:
        assert SettingsRegistry.get_definition("missing", "key") is None

    def test_all_definitions_returns_all(self) -> None:
        assert len(SettingsRegistry.all_definitions()) == 6

    def test_get_namespaces(self) -> None:
        assert SettingsRegistry.get_namespaces() == {
            "api",
            "billing",
            "features",
            "notifications",
            "ui",
        }

    def test_get_settings_by_namespace(self) -> None:
        settings = SettingsRegistry.get_settings_by_namespace("billing")
        assert set(settings) == {"plan_code", "trial_days"}

    def test_validate_value_int(self) -> None:
        assert SettingsRegistry.validate_value("api", "page_size", "50") == 50

    def test_validate_value_bool(self) -> None:
        assert SettingsRegistry.validate_value("features", "signup_enabled", "yes") is True

    def test_validate_value_list_json(self) -> None:
        assert SettingsRegistry.validate_value(
            "notifications",
            "channels",
            '["email", "sms"]',
        ) == [
            "email",
            "sms",
        ]

    def test_validate_value_dict_json(self) -> None:
        assert SettingsRegistry.validate_value("ui", "theme_config", '{"default":"dark"}') == {
            "default": "dark"
        }

    def test_validate_value_choice_and_validator(self) -> None:
        assert SettingsRegistry.validate_value("billing", "plan_code", "PRO") == "pro"

    def test_validate_value_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="below minimum"):
            SettingsRegistry.validate_value("billing", "trial_days", "0")

    def test_validate_value_rejects_unknown_setting(self) -> None:
        with pytest.raises(KeyError, match="missing.key"):
            SettingsRegistry.validate_value("missing", "key", "value")

    def test_serialize_value(self) -> None:
        assert SettingsRegistry.serialize_value(True) == "true"
        assert SettingsRegistry.serialize_value({"default": "light"}) == '{"default": "light"}'

    @override_settings(
        SYSTEM_RESGISTRY_DEFINITIONS={
            ("billing", "trial_days"): {
                "type": int,
                "default": 21,
                "description": "Override value.",
            }
        }
    )
    def test_settings_override_provider_values(self) -> None:
        assert SettingsRegistry.get_default_value("billing", "trial_days") == 21

    @override_settings(
        SYSTEM_RESGISTRY_DEFINITIONS={
            ("broken", "setting"): {
                "default": 10,
            }
        }
    )
    def test_invalid_definition_raises(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="missing 'type'"):
            SettingsRegistry.all_definitions()
