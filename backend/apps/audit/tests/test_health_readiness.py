from unittest.mock import patch

import pytest
from django.test import Client, override_settings
from django.utils.dateparse import parse_datetime

pytestmark = pytest.mark.django_db


@override_settings(
    FRONTEND_URL="https://demo.bidals.com",
    SECRET_KEY="test-secret-value",
    SENTRY_ENVIRONMENT="production",
)
def test_root_and_api_health_endpoints_return_safe_diagnostic_status(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgres://db_user:db-secret@db.internal:5432/bidals")
    monkeypatch.setenv("API_TOKEN", "token-secret-value")
    client = Client()

    root_response = client.get("/health/")
    api_response = client.get("/api/health/")

    assert root_response.status_code == 200
    assert api_response.status_code == 200

    root_payload = root_response.json()
    payload = api_response.json()
    assert {
        key: value
        for key, value in root_payload.items()
        if key != "server_time"
    } == {
        key: value
        for key, value in payload.items()
        if key != "server_time"
    }
    assert parse_datetime(root_payload["server_time"]) is not None
    assert set(payload) == {
        "status",
        "service",
        "environment",
        "allowed_frontend",
        "server_time",
        "demo_seed_available",
    }
    assert payload["status"] == "ok"
    assert payload["service"] == "bidals-backend"
    assert payload["environment"] == "staging"
    assert payload["allowed_frontend"] == "https://demo.bidals.com"
    assert parse_datetime(payload["server_time"]) is not None
    assert payload["demo_seed_available"] is True

    rendered = api_response.content.decode()
    assert "test-secret-value" not in rendered
    assert "db-secret" not in rendered
    assert "token-secret-value" not in rendered
    assert "DATABASE_URL" not in rendered
    assert "API_TOKEN" not in rendered


@override_settings(USE_REDIS_CACHE=False, SECRET_KEY="test-secret")
def test_readiness_endpoint_checks_database_and_does_not_leak_secrets():
    response = Client().get("/health/ready/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "bidals-backend"
    assert payload["checks"] == {"database": "ok", "cache": "skipped"}
    assert "test-secret" not in response.content.decode()


@override_settings(USE_REDIS_CACHE=True)
def test_readiness_endpoint_reports_cache_failure_without_secret_details():
    with patch("bidals.views.cache.set", side_effect=ConnectionError("redis-url-with-secret")):
        response = Client().get("/api/health/ready/")

    payload = response.json()
    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["cache"] == "error"
    assert "redis-url-with-secret" not in response.content.decode()
