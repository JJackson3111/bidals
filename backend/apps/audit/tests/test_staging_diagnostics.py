from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command, get_commands
from django.test import override_settings

from apps.audit.services.staging_diagnostics import mask_url, url_fingerprint


def test_deployment_fingerprint_command_exists():
    assert "deployment_fingerprint" in get_commands()


def test_deployment_fingerprint_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://db_user:db-secret@postgres.internal:5432/bidals")
    monkeypatch.setenv("REDIS_URL", "redis://redis_user:redis-secret@redis.internal:6379/0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "django-secret-value")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890abcdef1234567890abcdef12")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "tighten-seller-browse-isolation")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "bidals-backend-staging")
    output = StringIO()

    call_command("deployment_fingerprint", stdout=output)

    rendered = output.getvalue()
    assert "deployment_fingerprint" in rendered
    assert "git_commit_sha=abcdef1234567890abcdef1234567890abcdef12" in rendered
    assert "git_branch=tighten-seller-browse-isolation" in rendered
    assert "render_service_name=bidals-backend-staging" in rendered
    assert "file_staging_env_diagnostics.py=True" in rendered
    assert "file_staging_lifecycle_readiness.py=True" in rendered
    assert "deployment_fingerprint" in rendered
    assert "staging_env_diagnostics" in rendered
    assert "staging_lifecycle_readiness" in rendered
    assert "DATABASE_URL" not in rendered
    assert "REDIS_URL" not in rendered
    assert "SECRET_KEY" not in rendered
    assert "db_user" not in rendered
    assert "db-secret" not in rendered
    assert "redis_user" not in rendered
    assert "redis-secret" not in rendered
    assert "django-secret-value" not in rendered


def test_mask_url_hides_credentials_and_query_values():
    postgres_url = "postgres://db_user:db-pass@postgres.internal:5432/bidals?sslmode=require"
    redis_url = "redis://:redis-token@redis.internal:6379/0"

    masked_postgres = mask_url(postgres_url)
    masked_redis = mask_url(redis_url)
    fingerprint = url_fingerprint(postgres_url)

    assert masked_postgres == "postgres://***:***@postgres.internal:5432/bidals?query=present"
    assert masked_redis == "redis://:***@redis.internal:6379/0"
    assert fingerprint.startswith("sha256:")
    assert "db_user" not in masked_postgres
    assert "db-pass" not in masked_postgres
    assert "sslmode=require" not in masked_postgres
    assert "redis-token" not in masked_redis
    assert "db-pass" not in fingerprint


@override_settings(
    REDIS_URL="redis://diagnostic_user:redis-secret-token@redis.internal:6379/0",
    USE_REDIS_CACHE=True,
)
def test_staging_env_diagnostics_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://db_user:db-secret@postgres.internal:5432/bidals")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "django-secret-value")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    output = StringIO()

    with patch(
        "apps.audit.services.staging_diagnostics.redis_connection_status",
        return_value=("PASS", "ping succeeded"),
    ):
        call_command("staging_env_diagnostics", stdout=output)

    rendered = output.getvalue()
    assert "redis://***:***@redis.internal:6379/0" in rendered
    assert "redis_connection=PASS (ping succeeded)" in rendered
    assert "abcdef1234567890" in rendered
    assert "diagnostic_user" not in rendered
    assert "redis-secret-token" not in rendered
    assert "db_user" not in rendered
    assert "db-secret" not in rendered
    assert "django-secret-value" not in rendered
    assert "DATABASE_URL" not in rendered
    assert "SECRET_KEY" not in rendered


@override_settings(USE_TZ=False, TIME_ZONE="Europe/London")
@pytest.mark.django_db
def test_staging_lifecycle_readiness_reports_failures_safely(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://bad_user:bad-token@redis.internal:6379/0")
    output = StringIO()

    with (
        patch("apps.audit.services.staging_diagnostics.database_timezone", return_value=("Europe/London", None)),
        patch("apps.audit.services.staging_diagnostics.get_applied_migrations", return_value=set()),
    ):
        call_command("staging_lifecycle_readiness", stdout=output)

    rendered = output.getvalue()
    assert "[FAIL] USE_TZ: USE_TZ must be True." in rendered
    assert "[FAIL] TIME_ZONE: TIME_ZONE must be UTC." in rendered
    assert "[FAIL] DATABASE_TIMEZONE: timezone=Europe/London; expected UTC" in rendered
    assert "[FAIL] AUCTIONS_MIGRATION_0009" in rendered
    assert "[FAIL] AUDIT_MIGRATION_0011" in rendered
    assert "summary:" in rendered
    assert "bad_user" not in rendered
    assert "bad-token" not in rendered
