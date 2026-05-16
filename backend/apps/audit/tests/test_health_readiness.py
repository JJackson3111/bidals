from unittest.mock import patch

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


def test_root_and_api_health_endpoints_return_alive_status():
    client = Client()

    root_response = client.get("/health/")
    api_response = client.get("/api/health/")

    assert root_response.status_code == 200
    assert root_response.json() == {"status": "ok", "service": "bidals-backend"}
    assert api_response.status_code == 200
    assert api_response.json() == {"status": "ok", "service": "bidals-backend"}


@override_settings(USE_REDIS_CACHE=False, SECRET_KEY="super-secret-readiness-test-key")
def test_readiness_endpoint_checks_database_and_does_not_leak_secrets():
    response = Client().get("/health/ready/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "bidals-backend"
    assert payload["checks"] == {"database": "ok", "cache": "skipped"}
    assert "super-secret-readiness-test-key" not in response.content.decode()


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
