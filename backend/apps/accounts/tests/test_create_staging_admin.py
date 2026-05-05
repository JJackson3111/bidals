from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db


def test_create_staging_admin_requires_staging_or_force(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "production")
    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "StrongStagingPass123!")

    with pytest.raises(CommandError, match="outside BIDALS_ENV=staging"):
        call_command("create_staging_admin", stdout=StringIO())

    assert get_user_model().objects.count() == 0


def test_create_staging_admin_requires_password_env(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    monkeypatch.delenv("STAGING_ADMIN_PASSWORD", raising=False)

    with pytest.raises(CommandError, match="STAGING_ADMIN_PASSWORD must be set"):
        call_command("create_staging_admin", stdout=StringIO())


def test_create_staging_admin_creates_admin_without_printing_password(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "StrongStagingPass123!")
    output = StringIO()

    call_command(
        "create_staging_admin",
        username="stage_ops_admin",
        email="stage-ops@example.com",
        stdout=output,
    )

    rendered = output.getvalue()
    user = get_user_model().objects.get(email="stage-ops@example.com")
    assert user.username == "stage_ops_admin"
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password("StrongStagingPass123!")
    assert "StrongStagingPass123!" not in rendered
    assert "Password was read from environment" in rendered
    assert AuditLog.objects.filter(
        action=AuditAction.ADMIN_ACTION,
        entity_type="staging_admin",
        entity_id=str(user.id),
        metadata__created=True,
    ).exists()


def test_create_staging_admin_is_idempotent_and_updates_password(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "StrongStagingPass123!")
    call_command("create_staging_admin", stdout=StringIO())

    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "AnotherStrongPass123!")
    call_command("create_staging_admin", stdout=StringIO())

    User = get_user_model()
    user = User.objects.get(email="admin@bidals.staging.test")
    assert User.objects.filter(email="admin@bidals.staging.test").count() == 1
    assert user.check_password("AnotherStrongPass123!")
    assert AuditLog.objects.filter(
        action=AuditAction.ADMIN_ACTION,
        entity_type="staging_admin",
        entity_id=str(user.id),
        metadata__created=False,
    ).exists()


def test_create_staging_admin_refuses_ambiguous_existing_users(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "StrongStagingPass123!")
    User = get_user_model()
    User.objects.create_user(username="staging_admin", email="other@example.com", password="StrongPass123!")
    User.objects.create_user(username="other_admin", email="admin@bidals.staging.test", password="StrongPass123!")

    with pytest.raises(CommandError, match="different existing users"):
        call_command("create_staging_admin", stdout=StringIO())
