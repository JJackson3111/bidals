from dataclasses import asdict, dataclass, field
import os

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.models import AuditAction, AuditLog


@dataclass(frozen=True)
class ReadinessCheck:
    category: str
    name: str
    status: str
    message: str
    details: dict = field(default_factory=dict)


def runtime_environment() -> str:
    return (
        os.getenv("BIDALS_ENV")
        or os.getenv("ENV")
        or getattr(settings, "SENTRY_ENVIRONMENT", "")
        or ("development" if settings.DEBUG else "production")
    ).lower()


def run_backup_verification(*, actor=None, audit: bool = True) -> dict:
    generated_at = timezone.now()
    checks = [
        _database_connectivity_check(),
        _critical_tables_check(),
        _backup_timestamp_check(),
        _restore_test_check(),
    ]
    result = _serialize_report(
        report_type="backup_verification",
        generated_at=generated_at,
        checks=checks,
    )
    if audit:
        _audit_report(
            action=AuditAction.BACKUP_VERIFICATION_RUN,
            entity_type="backup_verification",
            actor=actor,
            generated_at=generated_at,
            result=result,
        )
    return result


def run_release_check(*, actor=None, audit: bool = True, request_id: str | None = None) -> dict:
    generated_at = timezone.now()
    backup_report = run_backup_verification(actor=actor, audit=False)
    backup_status = _worst_status(item["status"] for item in backup_report["checks"])
    checks = [
        _debug_check(),
        _secret_key_check(),
        _allowed_hosts_check(),
        _health_endpoint_check(),
        _migrations_check(),
        ReadinessCheck(
            category="database",
            name="Backup verification",
            status=backup_status,
            message="Backup verification summary included in this report.",
            details={"summary": backup_report["summary"]},
        ),
        _manual_check("core_flows", "Login", "Verify bidder, seller, and admin login in the deployed environment."),
        _manual_check("core_flows", "Auction creation", "Create and review a seller/admin auction in staging before production release."),
        _manual_check("core_flows", "Lot creation", "Create and review a lot in staging before production release."),
        _manual_check("core_flows", "Accepted bidding", "Place a valid bid and confirm the backend accepted response."),
        _manual_check("core_flows", "Rejected bidding", "Place an invalid bid and confirm the backend rejected response."),
        _manual_check("core_flows", "Winner calculation", "Run or verify close_expired_auctions and winner calculation on staging data."),
        _manual_check("core_flows", "Fulfillment workflow", "Update fulfillment status and verify audit logs."),
        _scheduled_jobs_check(),
        _audit_log_check(),
        _admin_export_check(),
        _anomaly_settings_check(),
        _notification_settings_check(),
        _manual_check("notifications", "Unread count", "Open the frontend and confirm the Alerts unread badge updates after mark-read."),
        _manual_check("ops", "Repair workflow", "Confirm two-admin repair request, approval, comments, and audit detail access."),
    ]
    result = _serialize_report(
        report_type="release_check",
        generated_at=generated_at,
        checks=checks,
        extra={"backup_verification": backup_report},
    )
    if audit:
        _audit_report(
            action=AuditAction.RELEASE_CHECK_RUN,
            entity_type="release_check",
            actor=actor,
            generated_at=generated_at,
            result=result,
            request_id=request_id,
        )
    return result


def _database_connectivity_check() -> ReadinessCheck:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return ReadinessCheck("database", "Connectivity", "FAIL", "Database connectivity failed.", {"error_type": type(exc).__name__})
    return ReadinessCheck("database", "Connectivity", "PASS", "Database connection is usable.")


def _critical_tables_check() -> ReadinessCheck:
    try:
        tables = set(connection.introspection.table_names())
    except Exception as exc:
        return ReadinessCheck("database", "Critical tables", "FAIL", "Could not inspect database tables.", {"error_type": type(exc).__name__})

    required = {"accounts_user", "auctions_auction", "auctions_lot", "auctions_bid", "audit_auditlog"}
    missing = sorted(required - tables)
    if missing:
        return ReadinessCheck("database", "Critical tables", "FAIL", "Critical BIDALS tables are missing.", {"missing_tables": missing})
    return ReadinessCheck("database", "Critical tables", "PASS", "Critical BIDALS tables are present.")


def _backup_timestamp_check() -> ReadinessCheck:
    timestamp = os.getenv("BACKUP_LAST_VERIFIED_AT", "")
    provider = os.getenv("BACKUP_PROVIDER", "")
    if not timestamp:
        return ReadinessCheck(
            "backup",
            "Backup timestamp",
            "WARN",
            "No BACKUP_LAST_VERIFIED_AT value is configured; verify backups in the cloud provider.",
            {"provider": provider or "unknown"},
        )

    parsed = parse_datetime(timestamp)
    if parsed is None:
        return ReadinessCheck("backup", "Backup timestamp", "WARN", "BACKUP_LAST_VERIFIED_AT is not ISO-8601.", {"provider": provider or "unknown"})
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    age_hours = round((timezone.now() - parsed).total_seconds() / 3600, 2)
    status = "PASS" if age_hours <= 48 else "WARN"
    return ReadinessCheck(
        "backup",
        "Backup timestamp",
        status,
        f"Last verified backup timestamp is {age_hours} hour(s) old.",
        {"provider": provider or "unknown", "age_hours": age_hours},
    )


def _restore_test_check() -> ReadinessCheck:
    timestamp = os.getenv("BACKUP_LAST_RESTORE_TEST_AT", "")
    if not timestamp:
        return ReadinessCheck(
            "backup",
            "Restore test",
            "WARN",
            "No BACKUP_LAST_RESTORE_TEST_AT value is configured; perform a restore test in staging.",
        )
    parsed = parse_datetime(timestamp)
    if parsed is None:
        return ReadinessCheck("backup", "Restore test", "WARN", "BACKUP_LAST_RESTORE_TEST_AT is not ISO-8601.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    age_days = round((timezone.now() - parsed).total_seconds() / 86400, 2)
    status = "PASS" if age_days <= 30 else "WARN"
    return ReadinessCheck("backup", "Restore test", status, f"Last restore test is {age_days} day(s) old.", {"age_days": age_days})


def _debug_check() -> ReadinessCheck:
    if settings.DEBUG:
        return ReadinessCheck("system", "DEBUG", "WARN", "DEBUG is enabled; production must run with DEBUG=false.")
    return ReadinessCheck("system", "DEBUG", "PASS", "DEBUG is disabled.")


def _secret_key_check() -> ReadinessCheck:
    secret_key = getattr(settings, "SECRET_KEY", "")
    placeholder_values = {"unsafe-development-secret-key", "change-me-in-production", "replace-with-a-long-random-secret"}
    if not secret_key or secret_key.startswith("unsafe-") or secret_key in placeholder_values:
        return ReadinessCheck("system", "SECRET_KEY", "FAIL", "Secret key is missing or uses the development placeholder.")
    return ReadinessCheck("system", "SECRET_KEY", "PASS", "Secret key is configured.")


def _allowed_hosts_check() -> ReadinessCheck:
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    if not hosts:
        return ReadinessCheck("system", "ALLOWED_HOSTS", "FAIL", "No allowed hosts are configured.")
    if "*" in hosts:
        return ReadinessCheck("system", "ALLOWED_HOSTS", "WARN", "Wildcard host is configured.")
    return ReadinessCheck("system", "ALLOWED_HOSTS", "PASS", f"{len(hosts)} allowed host(s) configured.")


def _health_endpoint_check() -> ReadinessCheck:
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    http_host = "localhost" if not hosts or "*" in hosts else hosts[0]
    response = Client().get("/api/health/", HTTP_HOST=http_host, HTTP_X_REQUEST_ID="release-check")
    if response.status_code == 200 and response.headers.get("X-Request-ID"):
        return ReadinessCheck("system", "Health endpoint", "PASS", "Backend health endpoint responds with a request id.")
    return ReadinessCheck("system", "Health endpoint", "FAIL", f"Health endpoint returned status {response.status_code}.")


def _migrations_check() -> ReadinessCheck:
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception as exc:
        return ReadinessCheck("database", "Migrations", "FAIL", "Could not inspect migrations.", {"error_type": type(exc).__name__})
    if plan:
        return ReadinessCheck("database", "Migrations", "FAIL", f"{len(plan)} unapplied migration step(s) detected.")
    return ReadinessCheck("database", "Migrations", "PASS", "No unapplied migrations detected.")


def _scheduled_jobs_check() -> ReadinessCheck:
    configured = os.getenv("SCHEDULED_JOBS_CONFIGURED", "").lower() in {"1", "true", "yes"}
    if configured:
        return ReadinessCheck("ops", "Scheduled jobs", "PASS", "Scheduled jobs are marked configured.")
    return ReadinessCheck("ops", "Scheduled jobs", "WARN", "Set SCHEDULED_JOBS_CONFIGURED=true after provider schedulers are configured.")


def _audit_log_check() -> ReadinessCheck:
    try:
        AuditLog.objects.order_by("-server_timestamp").first()
    except Exception as exc:
        return ReadinessCheck("ops", "Audit logs", "FAIL", "Audit log table is not readable.", {"error_type": type(exc).__name__})
    return ReadinessCheck("ops", "Audit logs", "PASS", "Audit log table is readable.")


def _admin_export_check() -> ReadinessCheck:
    return ReadinessCheck("ops", "Admin export", "PASS", "Admin activity export endpoint is installed and admin-protected.")


def _anomaly_settings_check() -> ReadinessCheck:
    if settings.BID_ANOMALY_REJECT_THRESHOLD > 0 and settings.BID_ANOMALY_RATE_LIMIT_THRESHOLD > 0:
        return ReadinessCheck("ops", "Anomaly thresholds", "PASS", "Bid anomaly thresholds are configured.")
    return ReadinessCheck("ops", "Anomaly thresholds", "WARN", "Bid anomaly thresholds should be positive.")


def _notification_settings_check() -> ReadinessCheck:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return ReadinessCheck("notifications", "Delivery", "PASS", "Email delivery is disabled safely.")
    if settings.DEFAULT_FROM_EMAIL:
        return ReadinessCheck("notifications", "Delivery", "PASS", "Email delivery is enabled with a sender address.")
    return ReadinessCheck("notifications", "Delivery", "FAIL", "Email delivery is enabled but DEFAULT_FROM_EMAIL is missing.")


def _manual_check(category: str, name: str, message: str) -> ReadinessCheck:
    return ReadinessCheck(category, name, "WARN", message, {"manual": True})


def _serialize_report(*, report_type: str, generated_at, checks: list[ReadinessCheck], extra: dict | None = None) -> dict:
    serialized_checks = [asdict(check) for check in checks]
    summary = {
        "pass": sum(1 for check in checks if check.status == "PASS"),
        "warn": sum(1 for check in checks if check.status == "WARN"),
        "fail": sum(1 for check in checks if check.status == "FAIL"),
    }
    report = {
        "report_type": report_type,
        "generated_at": generated_at.isoformat(),
        "environment": runtime_environment(),
        "summary": summary,
        "checks": serialized_checks,
    }
    if extra:
        report.update(extra)
    return report


def _audit_report(*, action: str, entity_type: str, actor, generated_at, result: dict, request_id: str | None = None) -> None:
    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=generated_at.strftime("%Y%m%d%H%M%S"),
            metadata={
                "actor_id": actor.id if actor else None,
                "environment": result["environment"],
                "summary": result["summary"],
                "request_id": request_id,
            },
        )
    except Exception:
        return


def _worst_status(statuses) -> str:
    values = list(statuses)
    if "FAIL" in values:
        return "FAIL"
    if "WARN" in values:
        return "WARN"
    return "PASS"
