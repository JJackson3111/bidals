from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.audit.services.readiness import runtime_environment

HEALTH_CHECK_PATH = "/api/health/"


@dataclass(frozen=True)
class DeploymentCheckResult:
    status: str
    name: str
    message: str


class Command(BaseCommand):
    help = "Run BIDALS staging/production deployment safety checks without printing secrets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--production",
            action="store_true",
            help="Treat production hardening issues as failures instead of local-development warnings.",
        )
        parser.add_argument(
            "--fail-on-warn",
            action="store_true",
            help="Exit non-zero when warnings are present.",
        )

    def handle(self, *args, **options):
        production = options["production"]
        checks = [
            _check_debug(production=production),
            _check_secret_key(production=production),
            _check_allowed_hosts(production=production),
            _check_database(production=production),
            _check_redis(production=production),
            _check_storage(production=production),
            _check_email(),
            _check_migrations(),
            _check_health_endpoint(),
        ]

        for check in checks:
            self.stdout.write(f"[{check.status}] {check.name}: {check.message}")

        _audit_deployment_check(checks=checks, production=production)

        failures = [check for check in checks if check.status == "FAIL"]
        warnings = [check for check in checks if check.status == "WARN"]
        if failures or (warnings and options["fail_on_warn"]):
            raise CommandError(
                f"Deployment check failed with {len(failures)} failure(s) and {len(warnings)} warning(s)."
            )

        self.stdout.write(self.style.SUCCESS("Deployment check completed."))


def _check_debug(*, production: bool) -> DeploymentCheckResult:
    if settings.DEBUG:
        status = "FAIL" if production else "WARN"
        return DeploymentCheckResult(status, "DEBUG", "DEBUG is enabled.")
    return DeploymentCheckResult("PASS", "DEBUG", "DEBUG is disabled.")


def _check_secret_key(*, production: bool) -> DeploymentCheckResult:
    secret_key = getattr(settings, "SECRET_KEY", "")
    placeholder_values = {"unsafe-development-secret-key", "change-me-in-production", "replace-with-a-long-random-secret"}
    unsafe = not secret_key or secret_key.startswith("unsafe-") or secret_key in placeholder_values
    if unsafe:
        status = "FAIL" if production else "WARN"
        return DeploymentCheckResult(status, "SECRET_KEY", "Secret key is missing or uses a development placeholder.")
    return DeploymentCheckResult("PASS", "SECRET_KEY", "Secret key is configured.")


def _check_allowed_hosts(*, production: bool) -> DeploymentCheckResult:
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    if not hosts:
        return DeploymentCheckResult("FAIL", "ALLOWED_HOSTS", "No allowed hosts are configured.")
    if production and set(hosts).issubset({"localhost", "127.0.0.1", "0.0.0.0", "backend"}):
        return DeploymentCheckResult("FAIL", "ALLOWED_HOSTS", "Only local allowed hosts are configured.")
    if "*" in hosts:
        status = "FAIL" if production else "WARN"
        return DeploymentCheckResult(status, "ALLOWED_HOSTS", "Wildcard host is configured.")
    return DeploymentCheckResult("PASS", "ALLOWED_HOSTS", f"{len(hosts)} allowed host(s) configured.")


def _check_database(*, production: bool) -> DeploymentCheckResult:
    engine = settings.DATABASES["default"]["ENGINE"]
    if production and engine.endswith("sqlite3"):
        return DeploymentCheckResult("FAIL", "DATABASE", "SQLite is configured for a production check.")
    return DeploymentCheckResult("PASS", "DATABASE", "Database engine is configured.")


def _check_redis(*, production: bool) -> DeploymentCheckResult:
    if getattr(settings, "USE_REDIS_CACHE", False):
        if getattr(settings, "REDIS_URL", ""):
            return DeploymentCheckResult("PASS", "REDIS", "Redis cache is enabled.")
        return DeploymentCheckResult("FAIL", "REDIS", "Redis cache is enabled but REDIS_URL is missing.")
    status = "WARN" if production else "PASS"
    return DeploymentCheckResult(status, "REDIS", "Redis cache is disabled; production throttling should use Redis.")


def _check_storage(*, production: bool) -> DeploymentCheckResult:
    if getattr(settings, "USE_S3", False):
        return DeploymentCheckResult("PASS", "MEDIA_STORAGE", "Object storage is enabled.")
    if getattr(settings, "SERVE_LOCAL_MEDIA", False):
        status = "FAIL" if runtime_environment() == "production" else "WARN"
        return DeploymentCheckResult(status, "MEDIA_STORAGE", "Local media serving is enabled; use this only for staging/local demos.")
    status = "WARN" if production else "PASS"
    return DeploymentCheckResult(status, "MEDIA_STORAGE", "Local media storage is configured.")


def _check_email() -> DeploymentCheckResult:
    if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False):
        return DeploymentCheckResult("PASS", "EMAIL", "Email notification delivery is disabled.")

    backend = getattr(settings, "EMAIL_BACKEND", "")
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    host = getattr(settings, "EMAIL_HOST", "")
    if not from_email:
        return DeploymentCheckResult("FAIL", "EMAIL", "Email delivery is enabled but DEFAULT_FROM_EMAIL is missing.")
    if backend.endswith("smtp.EmailBackend") and not host:
        return DeploymentCheckResult("FAIL", "EMAIL", "SMTP email delivery is enabled but EMAIL_HOST is missing.")
    return DeploymentCheckResult("PASS", "EMAIL", "Email notification settings are configured.")


def _check_migrations() -> DeploymentCheckResult:
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception as exc:
        return DeploymentCheckResult("FAIL", "MIGRATIONS", f"Could not inspect migrations: {exc.__class__.__name__}.")

    if plan:
        return DeploymentCheckResult("FAIL", "MIGRATIONS", f"{len(plan)} unapplied migration step(s) detected.")
    return DeploymentCheckResult("PASS", "MIGRATIONS", "No unapplied migrations detected.")


def _check_health_endpoint() -> DeploymentCheckResult:
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    http_host = "localhost" if not hosts or "*" in hosts else hosts[0]
    response = Client().get(HEALTH_CHECK_PATH, follow=True, HTTP_HOST=http_host, HTTP_X_REQUEST_ID="deployment-check")
    if response.status_code == 200 and response.headers.get("X-Request-ID"):
        return DeploymentCheckResult(
            "PASS",
            "HEALTH",
            f"Backend health endpoint {HEALTH_CHECK_PATH} responds with a request id.",
        )
    return DeploymentCheckResult("FAIL", "HEALTH", f"Health endpoint {HEALTH_CHECK_PATH} returned status {response.status_code}.")


def _audit_deployment_check(*, checks: list[DeploymentCheckResult], production: bool) -> None:
    try:
        AuditLog.objects.create(
            actor=None,
            action=AuditAction.DEPLOYMENT_CHECK_RUN,
            entity_type="deployment_check",
            entity_id=timezone.now().strftime("%Y%m%d%H%M%S"),
            metadata={
                "production": production,
                "pass_count": sum(1 for check in checks if check.status == "PASS"),
                "warn_count": sum(1 for check in checks if check.status == "WARN"),
                "fail_count": sum(1 for check in checks if check.status == "FAIL"),
                "failed_checks": [check.name for check in checks if check.status == "FAIL"],
            },
        )
    except Exception:
        return
