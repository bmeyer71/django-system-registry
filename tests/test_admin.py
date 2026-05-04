from __future__ import annotations

from typing import Any, cast

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest
from django.test.client import RequestFactory

from system_resgistry.admin import SystemSettingAdmin
from system_resgistry.models import SystemSetting


@pytest.mark.django_db
class TestSystemSettingAdmin:
    def test_reset_to_default_action(self) -> None:
        setting = SystemSetting.set_value("billing", "trial_days", 21)
        admin = SystemSettingAdmin(SystemSetting, AdminSite())
        request = self._build_request()

        admin.reset_to_default(request, SystemSetting.objects.filter(pk=setting.pk))

        setting.refresh_from_db()
        assert setting.typed_value == 14

    def test_validate_settings_action_reports_success(self) -> None:
        setting = SystemSetting.set_value("features", "signup_enabled", True)
        admin = SystemSettingAdmin(SystemSetting, AdminSite())
        request = self._build_request()

        admin.validate_settings(request, SystemSetting.objects.filter(pk=setting.pk))

        messages = list(request._messages)  # type: ignore[attr-defined]
        assert len(messages) == 1
        assert "All 1 setting(s) are valid." in str(messages[0])

    @staticmethod
    def _build_request() -> HttpRequest:
        request = RequestFactory().post("/admin/system_resgistry/systemsetting/")
        request.session = SessionStore()
        request_with_messages = cast(Any, request)
        request_with_messages._messages = FallbackStorage(request)
        return request
