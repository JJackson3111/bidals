from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(
    SECRET_KEY="release-check-test-secret",
    DEBUG=False,
    ALLOWED_HOSTS=["localhost", "testserver"],
    USE_REDIS_CACHE=False,
    USE_S3=False,
    EMAIL_NOTIFICATIONS_ENABLED=False,
)
def test_verify_backup_command_outputs_structure_and_audits(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    output = StringIO()

    call_command("verify_backup", stdout=output)

    rendered = output.getvalue()
    assert "[PASS] database / Connectivity" in rendered
    assert "Backup verification completed." in rendered
    assert AuditLog.objects.filter(action=AuditAction.BACKUP_VERIFICATION_RUN).exists()


@override_settings(
    SECRET_KEY="release-check-test-secret",
    DEBUG=False,
    ALLOWED_HOSTS=["localhost", "testserver"],
    USE_REDIS_CACHE=False,
    USE_S3=False,
    EMAIL_NOTIFICATIONS_ENABLED=False,
)
def test_release_check_command_outputs_report_without_secrets(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    output = StringIO()

    call_command("release_check", stdout=output)

    rendered = output.getvalue()
    assert "Release readiness report generated" in rendered
    assert "[PASS] system / Health endpoint" in rendered
    assert "/api/health/" in rendered
    assert "system / SECRET_KEY" in rendered
    assert "release-check-test-secret" not in rendered
    assert AuditLog.objects.filter(action=AuditAction.RELEASE_CHECK_RUN).exists()


@override_settings(
    SECRET_KEY="release-check-test-secret",
    DEBUG=False,
    ALLOWED_HOSTS=["localhost", "testserver"],
    USE_REDIS_CACHE=False,
    USE_S3=False,
    EMAIL_NOTIFICATIONS_ENABLED=False,
)
def test_admin_release_check_endpoint_is_admin_only(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    admin = create_user("admin", role=UserRole.ADMIN)
    seller = create_user("seller", role=UserRole.SELLER)

    admin_response = authenticated_client(admin).get("/api/admin/release-check/")
    seller_response = authenticated_client(seller).get("/api/admin/release-check/")
    anonymous_response = APIClient().get("/api/admin/release-check/")

    assert admin_response.status_code == 200
    assert admin_response.data["report_type"] == "release_check"
    assert {"pass", "warn", "fail"}.issubset(admin_response.data["summary"])
    assert "backup_verification" in admin_response.data
    assert seller_response.status_code == 403
    assert anonymous_response.status_code == 401
    assert AuditLog.objects.filter(action=AuditAction.RELEASE_CHECK_RUN, actor=admin).exists()
