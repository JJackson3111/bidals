import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_security_rate_cache():
    cache.clear()
    yield
    cache.clear()


def create_user(username="bidder", role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def test_login_success_is_audited_without_logging_password_or_tokens():
    user = create_user()
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "StrongPass123!"},
        format="json",
        HTTP_USER_AGENT="security-test",
    )

    audit = AuditLog.objects.get(action=AuditAction.LOGIN_SUCCESS, actor=user)
    metadata = audit.metadata

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    assert metadata["actor_id"] == user.id
    assert metadata["actor_role"] == UserRole.BIDDER
    assert metadata["request_path"] == "/api/auth/login/"
    assert "StrongPass123!" not in str(metadata)
    assert "access" not in metadata
    assert "refresh" not in metadata


def test_failed_login_is_audited_without_logging_password():
    user = create_user()
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "WrongPass123!"},
        format="json",
    )

    audit = AuditLog.objects.get(action=AuditAction.LOGIN_FAILED)

    assert response.status_code == 401
    assert audit.actor is None
    assert audit.metadata["login_identifier"] == user.username
    assert "WrongPass123!" not in str(audit.metadata)


@override_settings(RATE_LIMIT_LOGIN="1/minute")
def test_repeated_login_attempts_are_rate_limited_and_audited():
    user = create_user()
    client = APIClient()

    first = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "WrongPass123!"},
        format="json",
    )
    second = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "WrongPass123!"},
        format="json",
    )

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.data["reason"] == "RATE_LIMITED"
    assert AuditLog.objects.filter(
        action=AuditAction.RATE_LIMIT_TRIGGERED,
        entity_type="rate_limit",
        entity_id="login",
    ).exists()


def test_logout_blacklists_refresh_token_and_is_audited():
    user = create_user()
    client = APIClient()
    login = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "StrongPass123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = client.post("/api/auth/logout/", {"refresh": login.data["refresh"]}, format="json")

    assert response.status_code == 204
    assert AuditLog.objects.filter(action=AuditAction.LOGOUT, actor=user).exists()


def test_token_refresh_is_audited():
    user = create_user()
    client = APIClient()
    login = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "StrongPass123!"},
        format="json",
    )

    response = client.post("/api/auth/refresh/", {"refresh": login.data["refresh"]}, format="json")

    assert response.status_code == 200
    assert "access" in response.data
    assert AuditLog.objects.filter(action=AuditAction.TOKEN_REFRESH, actor=user).exists()
