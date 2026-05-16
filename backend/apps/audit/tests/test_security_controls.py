import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from bidals.settings.validation import missing_required_production_env, validate_rate_limit_settings

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_security_cache():
    cache.clear()
    yield
    cache.clear()


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


@override_settings(CORS_ALLOWED_ORIGINS=["https://app.bidals.example"])
def test_configured_cors_origin_is_allowed_and_unknown_origin_is_rejected():
    client = Client()

    allowed = client.get("/api/health/", HTTP_ORIGIN="https://app.bidals.example")
    unknown = client.get("/api/health/", HTTP_ORIGIN="https://evil.example")

    assert allowed.status_code == 200
    assert allowed["Access-Control-Allow-Origin"] == "https://app.bidals.example"
    assert unknown.status_code == 200
    assert "Access-Control-Allow-Origin" not in unknown


def test_production_env_validation_reports_all_missing_critical_values(monkeypatch):
    for name in (
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DATABASE_URL",
        "DJANGO_DATABASE_URL",
        "FRONTEND_URL",
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)

    missing = missing_required_production_env()

    assert "DJANGO_SECRET_KEY" in missing
    assert "DJANGO_ALLOWED_HOSTS" in missing
    assert "DATABASE_URL or DJANGO_DATABASE_URL" in missing
    assert "FRONTEND_URL or DJANGO_CORS_ALLOWED_ORIGINS" in missing
    assert "FRONTEND_URL or DJANGO_CSRF_TRUSTED_ORIGINS" in missing


def test_invalid_rate_limit_values_fail_validation_before_request_time():
    with pytest.raises(ImproperlyConfigured, match="RATE_LIMIT_LOGIN"):
        validate_rate_limit_settings(
            {
                "RATE_LIMIT_LOGIN": "fast",
                "RATE_LIMIT_REGISTRATION": "5/minute",
                "RATE_LIMIT_BID_CREATE": "",
                "RATE_LIMIT_PASSWORD_RESET": "3/hour",
                "RATE_LIMIT_ADMIN_ACTIONS": "30/minute",
            }
        )


def test_blank_bid_create_rate_limit_is_valid_for_bid_specific_fallback():
    validate_rate_limit_settings(
        {
            "RATE_LIMIT_LOGIN": "5/minute",
            "RATE_LIMIT_REGISTRATION": "5/minute",
            "RATE_LIMIT_BID_CREATE": "",
            "RATE_LIMIT_PASSWORD_RESET": "3/hour",
            "RATE_LIMIT_ADMIN_ACTIONS": "30/minute",
        }
    )


def test_permission_denied_is_audited_for_admin_only_endpoint():
    seller = create_user("seller", role=UserRole.SELLER)

    response = authenticated_client(seller).get("/api/admin/activity/export/")

    assert response.status_code == 403
    assert AuditLog.objects.filter(
        action=AuditAction.PERMISSION_DENIED,
        actor=seller,
        metadata__request_path="/api/admin/activity/export/",
        metadata__status_code=403,
    ).exists()


@override_settings(RATE_LIMIT_ADMIN_ACTIONS="1/minute")
def test_sensitive_admin_actions_are_rate_limited_and_audited():
    admin = create_user("admin", role=UserRole.ADMIN)
    client = authenticated_client(admin)

    first = client.get("/api/admin/activity/export/")
    second = client.get("/api/admin/activity/export/")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.data["reason"] == "RATE_LIMITED"
    assert AuditLog.objects.filter(
        action=AuditAction.RATE_LIMIT_TRIGGERED,
        actor=admin,
        entity_id="admin_activity_export",
    ).exists()


@override_settings(
    PERMISSIONS_POLICY="camera=(), microphone=(), geolocation=(), payment=()",
    CONTENT_SECURITY_POLICY="default-src 'self'",
    CONTENT_SECURITY_POLICY_REPORT_ONLY=True,
)
def test_security_headers_are_added_without_forcing_blocking_csp():
    response = Client().get("/api/health/")

    assert response["Permissions-Policy"] == "camera=(), microphone=(), geolocation=(), payment=()"
    assert response["Content-Security-Policy-Report-Only"] == "default-src 'self'"
