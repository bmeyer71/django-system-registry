from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.html import format_html

from system_resgistry.models import SystemSetting
from system_resgistry.registry import SettingsRegistry


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "namespace",
        "key",
        "typed_value_display",
        "expected_type_display",
        "default_value_display",
        "updated_at",
    )
    list_filter = ("namespace", "updated_at")
    search_fields = ("namespace", "key", "description")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "expected_type_display",
        "default_value_display",
    )
    ordering = ("namespace", "key")
    actions = ("reset_to_default", "validate_settings")

    fieldsets = (
        (None, {"fields": ("namespace", "key", "value", "description")}),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "expected_type_display",
                    "default_value_display",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_form(  # type: ignore[override]
        self,
        request: HttpRequest,
        obj: Any = None,
        **kwargs: Any,
    ) -> Any:
        form = super().get_form(request, obj, **kwargs)
        if obj is not None:
            definition = SettingsRegistry.get_definition(obj.namespace, obj.key)
            if definition is not None:
                value_type = getattr(definition["type"], "__name__", repr(definition["type"]))
                form.base_fields["value"].help_text = (
                    f"Expected type: {value_type} · Default: {definition['default']!r}"
                )
        return form

    @admin.display(description="Current value")
    def typed_value_display(self, obj: SystemSetting) -> str:
        value = obj.typed_value
        if isinstance(value, bool):
            return "Yes" if value else "No"
        text = str(value)
        if len(text) > 80:
            return f"{text[:77]}..."
        return text

    @admin.display(description="Expected type")
    def expected_type_display(self, obj: SystemSetting) -> str:
        type_name = getattr(obj.expected_type, "__name__", repr(obj.expected_type))
        return format_html("<code>{}</code>", type_name)

    @admin.display(description="Default value")
    def default_value_display(self, obj: SystemSetting) -> str:
        return str(obj.default_value)

    @admin.action(description="Reset selected settings to registry defaults")
    def reset_to_default(self, request: HttpRequest, queryset: Any) -> None:
        reset_count = 0
        for setting in queryset:
            definition = SettingsRegistry.get_definition(setting.namespace, setting.key)
            if definition is None:
                continue

            SystemSetting.set_value(
                setting.namespace,
                setting.key,
                definition["default"],
                description=definition["description"],
            )
            reset_count += 1

        self.message_user(
            request,
            f"Reset {reset_count} setting(s) to their default values.",
            messages.SUCCESS,
        )

    @admin.action(description="Validate selected settings against registry")
    def validate_settings(self, request: HttpRequest, queryset: Any) -> None:
        errors: list[str] = []
        for setting in queryset:
            try:
                setting.full_clean()
            except ValidationError as exc:
                errors.append(f"{setting}: {exc}")

        if errors:
            self.message_user(
                request,
                "Validation issues: " + "; ".join(errors),
                messages.WARNING,
            )
            return

        self.message_user(
            request,
            f"All {queryset.count()} setting(s) are valid.",
            messages.SUCCESS,
        )
