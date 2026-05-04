from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.audit.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db


def test_deployment_check_runs_locally_and_audits():
    output = StringIO()

    call_command("deployment_check", stdout=output)

    rendered = output.getvalue()
    assert "[PASS]" in rendered
    assert "Deployment check completed." in rendered
    assert AuditLog.objects.filter(action=AuditAction.DEPLOYMENT_CHECK_RUN).exists()


@override_settings(
    DEBUG=True,
    SECRET_KEY="unsafe-development-secret-key",
    ALLOWED_HOSTS=["localhost"],
    USE_REDIS_CACHE=False,
    USE_S3=False,
    EMAIL_NOTIFICATIONS_ENABLED=False,
)
def test_deployment_check_production_mode_fails_without_printing_secrets():
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("deployment_check", production=True, stdout=output)

    rendered = output.getvalue()
    assert "[FAIL] DEBUG" in rendered
    assert "[FAIL] SECRET_KEY" in rendered
    assert "unsafe-development-secret-key" not in rendered
