from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from system_resgistry.models import SystemSetting
from system_resgistry.registry import SettingsRegistry


class Command(BaseCommand):
    help = "Synchronize database-backed settings with the registered setting definitions."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
        parser.add_argument("--namespace", type=str, help="Only sync one namespace")
        parser.add_argument("--list-namespaces", action="store_true", help="List namespaces")
        parser.add_argument(
            "--list-settings",
            type=str,
            metavar="NAMESPACE",
            help="List settings for a namespace",
        )
        parser.add_argument("--verbose", action="store_true", help="Print per-setting output")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list_namespaces"]:
            self._list_namespaces()
            return

        list_settings = options["list_settings"]
        if list_settings:
            self._list_settings(list_settings)
            return

        namespace = options["namespace"]
        if namespace and namespace not in SettingsRegistry.get_namespaces():
            raise CommandError(f"Unknown namespace '{namespace}'.")

        self._sync(
            dry_run=options["dry_run"],
            namespace=namespace,
            verbose=options["verbose"],
        )

    def _list_namespaces(self) -> None:
        namespaces = sorted(SettingsRegistry.get_namespaces())
        if not namespaces:
            self.stdout.write(self.style.WARNING("No namespaces registered."))
            return

        self.stdout.write("Registered namespaces:")
        for namespace in namespaces:
            count = len(SettingsRegistry.get_settings_by_namespace(namespace))
            self.stdout.write(f"  {namespace} ({count} settings)")

    def _list_settings(self, namespace: str) -> None:
        settings = SettingsRegistry.get_settings_by_namespace(namespace)
        if not settings:
            raise CommandError(f"No settings found for namespace '{namespace}'.")

        self.stdout.write(f"Settings for '{namespace}':")
        for key, definition in sorted(settings.items()):
            type_name = getattr(definition["type"], "__name__", repr(definition["type"]))
            self.stdout.write(
                f"  {key} ({type_name}, default={definition['default']!r}): "
                f"{definition['description']}"
            )

    def _sync(self, *, dry_run: bool, namespace: str | None, verbose: bool) -> None:
        definitions = SettingsRegistry.all_definitions()
        if namespace is not None:
            definitions = {
                (registered_namespace, key): definition
                for (registered_namespace, key), definition in definitions.items()
                if registered_namespace == namespace
            }

        created = 0
        updated = 0
        unchanged = 0

        for (registered_namespace, key), definition in sorted(definitions.items()):
            full_key = f"{registered_namespace}.{key}"
            default_value = SettingsRegistry.serialize_value(definition["default"])
            description = definition["description"]
            existing = SystemSetting.objects.filter(
                namespace=registered_namespace,
                key=key,
            ).first()

            if existing is None:
                created += 1
                if dry_run:
                    self.stdout.write(self.style.SUCCESS(f"  [create] {full_key}"))
                    continue

                SystemSetting.objects.create(
                    namespace=registered_namespace,
                    key=key,
                    value=default_value,
                    description=description,
                )
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"  Created {full_key}"))
                continue

            if existing.description != description:
                updated += 1
                if dry_run:
                    self.stdout.write(self.style.WARNING(f"  [update] {full_key} description"))
                    continue

                existing.description = description
                existing.save(update_fields=["description", "updated_at"])
                if verbose:
                    self.stdout.write(self.style.WARNING(f"  Updated {full_key} description"))
                continue

            unchanged += 1
            if verbose:
                self.stdout.write(f"  Unchanged {full_key}")

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}Summary: {created} created, {updated} updated, {unchanged} unchanged."
            )
        )
