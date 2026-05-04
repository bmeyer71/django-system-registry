from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from system_resgistry.models import SystemSetting


@pytest.mark.django_db
class TestSyncSystemSettingsCommand:
    def test_sync_creates_missing_settings(self) -> None:
        stdout = StringIO()
        call_command("sync_system_settings", stdout=stdout)
        assert SystemSetting.objects.count() == 6
        assert "Summary: 6 created, 0 updated, 0 unchanged." in stdout.getvalue()

    def test_sync_dry_run_does_not_write(self) -> None:
        stdout = StringIO()
        call_command("sync_system_settings", "--dry-run", stdout=stdout)
        assert SystemSetting.objects.count() == 0
        assert "[DRY RUN] Summary: 6 created, 0 updated, 0 unchanged." in stdout.getvalue()

    def test_sync_namespace_limits_scope(self) -> None:
        stdout = StringIO()
        call_command("sync_system_settings", "--namespace", "billing", stdout=stdout)
        assert SystemSetting.objects.count() == 2
        assert "Summary: 2 created, 0 updated, 0 unchanged." in stdout.getvalue()

    def test_list_namespaces(self) -> None:
        stdout = StringIO()
        call_command("sync_system_settings", "--list-namespaces", stdout=stdout)
        output = stdout.getvalue()
        assert "api (1 settings)" in output
        assert "billing (2 settings)" in output

    def test_list_settings(self) -> None:
        stdout = StringIO()
        call_command("sync_system_settings", "--list-settings", "billing", stdout=stdout)
        output = stdout.getvalue()
        assert "plan_code (str, default='starter')" in output
        assert "trial_days (int, default=14)" in output
