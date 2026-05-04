from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any, TypedDict, cast

from django.core.exceptions import ImproperlyConfigured

from system_resgistry.conf import get_registry_definitions

Validator = Callable[[Any], Any | None]
Coercer = Callable[[Any], Any]


class SettingDefinition(TypedDict, total=False):
    type: type[Any] | Coercer
    default: Any
    description: str
    choices: Iterable[Any]
    min_value: int | float
    max_value: int | float
    validator: Validator


class SettingsRegistry:
    """Runtime registry backed by host-supplied Django settings."""

    @classmethod
    def get_setting(cls, namespace: str, key: str) -> SettingDefinition:
        definition = cls.get_definition(namespace, key)
        if definition is None:
            msg = f"Setting '{namespace}.{key}' not found in registry"
            raise KeyError(msg)
        return definition

    @classmethod
    def get_definition(cls, namespace: str, key: str) -> SettingDefinition | None:
        raw_definition = get_registry_definitions().get((namespace, key))
        if raw_definition is None:
            return None
        return cls._normalize_definition(namespace, key, raw_definition)

    @classmethod
    def all_definitions(cls) -> dict[tuple[str, str], SettingDefinition]:
        return {
            (namespace, key): cls._normalize_definition(namespace, key, definition)
            for (namespace, key), definition in get_registry_definitions().items()
        }

    @classmethod
    def get_namespaces(cls) -> set[str]:
        return {namespace for namespace, _ in cls.all_definitions()}

    @classmethod
    def get_settings_by_namespace(cls, namespace: str) -> dict[str, SettingDefinition]:
        return {
            key: definition
            for (registered_namespace, key), definition in cls.all_definitions().items()
            if registered_namespace == namespace
        }

    @classmethod
    def get_default_value(cls, namespace: str, key: str) -> Any:
        return cls.get_setting(namespace, key)["default"]

    @classmethod
    def serialize_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True)
        return str(value)

    @classmethod
    def validate_value(cls, namespace: str, key: str, value: Any) -> Any:
        definition = cls.get_setting(namespace, key)
        expected_type = definition["type"]
        default_value = definition["default"]

        if value is None or (
            isinstance(value, str) and not value.strip() and expected_type is not str
        ):
            result = default_value
        else:
            result = cls._coerce_value(namespace, key, expected_type, value)

        validator = definition.get("validator")
        if validator is not None:
            validated = validator(result)
            if validated is not None:
                result = validated

        choices = definition.get("choices")
        if choices is not None and result not in choices:
            msg = f"Value {result!r} is not an allowed choice for {namespace}.{key}"
            raise ValueError(msg)

        min_value = definition.get("min_value")
        if min_value is not None and isinstance(result, (int, float)) and result < min_value:
            msg = f"Value {result!r} is below minimum {min_value} for {namespace}.{key}"
            raise ValueError(msg)

        max_value = definition.get("max_value")
        if max_value is not None and isinstance(result, (int, float)) and result > max_value:
            msg = f"Value {result!r} is above maximum {max_value} for {namespace}.{key}"
            raise ValueError(msg)

        return result

    @staticmethod
    def _normalize_definition(
        namespace: str,
        key: str,
        definition: dict[str, Any],
    ) -> SettingDefinition:
        if "type" not in definition:
            msg = f"Registry definition for {namespace}.{key} is missing 'type'."
            raise ImproperlyConfigured(msg)
        if "default" not in definition:
            msg = f"Registry definition for {namespace}.{key} is missing 'default'."
            raise ImproperlyConfigured(msg)

        normalized = cast(SettingDefinition, definition.copy())
        normalized.setdefault("description", "")
        return normalized

    @staticmethod
    def _coerce_value(
        namespace: str,
        key: str,
        expected_type: type[Any] | Coercer,
        value: Any,
    ) -> Any:
        if expected_type is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
            if value in {0, 1}:
                return bool(value)
            msg = f"Cannot convert {value!r} to bool for {namespace}.{key}"
            raise ValueError(msg)

        if expected_type is list:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            msg = f"Expected a JSON list for {namespace}.{key}"
            raise TypeError(msg)

        if expected_type is dict:
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            msg = f"Expected a JSON object for {namespace}.{key}"
            raise TypeError(msg)

        try:
            return expected_type(value)
        except (TypeError, ValueError) as exc:
            type_name = getattr(expected_type, "__name__", repr(expected_type))
            msg = f"Cannot convert {value!r} to {type_name} for {namespace}.{key}"
            raise ValueError(msg) from exc
