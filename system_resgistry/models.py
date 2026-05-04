from __future__ import annotations

import uuid
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from system_resgistry.cache import invalidate_cache_key
from system_resgistry.registry import SettingsRegistry


class SystemSetting(models.Model):
    """Database-backed application setting validated against the host registry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.CharField(max_length=50)
    key = models.CharField(max_length=100)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_resgistry_system_setting"
        ordering = ["namespace", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=("namespace", "key"),
                name="system_resgistry_namespace_key_unique",
            )
        ]
        indexes = [
            models.Index(fields=["namespace"]),
            models.Index(fields=["namespace", "key"]),
        ]

    def __str__(self) -> str:
        return f"{self.namespace}.{self.key}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        try:
            SettingsRegistry.get_setting(self.namespace, self.key)
        except KeyError as exc:
            msg = f"Setting '{self.namespace}.{self.key}' is not registered."
            raise ValidationError(msg) from exc

        try:
            SettingsRegistry.validate_value(self.namespace, self.key, self.value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                {"value": f"Invalid value for {self.namespace}.{self.key}: {exc}"}
            ) from exc

    @property
    def typed_value(self) -> Any:
        return SettingsRegistry.validate_value(self.namespace, self.key, self.value)

    @property
    def expected_type(self) -> type[Any]:
        definition = SettingsRegistry.get_setting(self.namespace, self.key)
        return cast(type[Any], definition["type"])

    @property
    def default_value(self) -> Any:
        return SettingsRegistry.get_default_value(self.namespace, self.key)

    @classmethod
    def get_value(cls, namespace: str, key: str, default: Any = None) -> Any:
        setting = cls.objects.filter(namespace=namespace, key=key).first()
        if setting is not None:
            return setting.typed_value

        definition = SettingsRegistry.get_definition(namespace, key)
        if definition is not None:
            return definition["default"]

        return default

    @classmethod
    def set_value(
        cls,
        namespace: str,
        key: str,
        value: Any,
        description: str | None = None,
    ) -> SystemSetting:
        validated_value = SettingsRegistry.validate_value(namespace, key, value)
        definition = SettingsRegistry.get_setting(namespace, key)
        stored_value = SettingsRegistry.serialize_value(validated_value)
        setting, _ = cls.objects.update_or_create(
            namespace=namespace,
            key=key,
            defaults={
                "value": stored_value,
                "description": (
                    description if description is not None else definition["description"]
                ),
            },
        )
        return setting

    @classmethod
    def get_namespace_settings(cls, namespace: str) -> dict[str, Any]:
        registered = SettingsRegistry.get_settings_by_namespace(namespace)
        values = {
            key: SettingsRegistry.get_default_value(namespace, key)
            for key in registered
        }
        for setting in cls.objects.filter(namespace=namespace):
            values[setting.key] = setting.typed_value
        return values

    @classmethod
    def sync_with_registry(cls, namespace: str | None = None) -> dict[str, int]:
        definitions = SettingsRegistry.all_definitions()
        if namespace is not None:
            definitions = {
                (registered_namespace, key): definition
                for (registered_namespace, key), definition in definitions.items()
                if registered_namespace == namespace
            }

        stats = {"created": 0, "updated": 0, "existing": 0}
        existing = {
            (setting.namespace, setting.key): setting
            for setting in cls.objects.all().only("id", "namespace", "key", "description")
        }

        for (registered_namespace, key), definition in definitions.items():
            description = str(definition["description"])
            default_value = SettingsRegistry.serialize_value(definition["default"])
            current = existing.get((registered_namespace, key))

            if current is None:
                cls.objects.create(
                    namespace=registered_namespace,
                    key=key,
                    value=default_value,
                    description=description,
                )
                stats["created"] += 1
                continue

            if current.description != description:
                current.description = description
                current.save(update_fields=["description", "updated_at"])
                stats["updated"] += 1
                continue

            stats["existing"] += 1

        return stats


@receiver(post_save, sender=SystemSetting)
@receiver(post_delete, sender=SystemSetting)
def invalidate_setting_cache(
    sender: type[SystemSetting],
    instance: SystemSetting,
    **kwargs: Any,
) -> None:
    del sender, kwargs
    invalidate_cache_key(instance.namespace, instance.key)
