from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management import get_commands
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.auctions.models import Auction, Lot, LotStatus, LotWinnerStatus
from apps.auctions.services.lifecycle import (
    ENDED_AUCTION_STATUS_ALIASES,
    LIVE_AUCTION_STATUS_ALIASES,
    SCHEDULED_AUCTION_STATUSES,
    get_effective_auction_status,
    get_effective_lot_status,
)

NOT_CONFIGURED = "not configured"
NOT_AVAILABLE = "not available"
TARGET_AUCTIONS_MIGRATION = "0009_alter_bid_rejection_reason"
TARGET_AUDIT_MIGRATION = "0011_alter_auditlog_action"
COMMAND_FILTER_TERMS = ("staging", "diagnostics", "lifecycle", "fingerprint")


@dataclass(frozen=True)
class DiagnosticLine:
    name: str
    value: str


@dataclass(frozen=True)
class ReadinessLine:
    status: str
    name: str
    message: str


def collect_staging_env_diagnostics() -> list[DiagnosticLine]:
    database_settings = settings.DATABASES["default"]
    redis_url = getattr(settings, "REDIS_URL", "")
    redis_status, redis_message = redis_connection_status(redis_url)
    db_timezone, db_timezone_error = database_timezone()

    return [
        DiagnosticLine("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", NOT_CONFIGURED)),
        DiagnosticLine("DEBUG", str(settings.DEBUG)),
        DiagnosticLine("USE_TZ", str(settings.USE_TZ)),
        DiagnosticLine("TIME_ZONE", settings.TIME_ZONE),
        DiagnosticLine("server_time", timezone.now().isoformat()),
        DiagnosticLine("database_engine", str(database_settings.get("ENGINE") or NOT_CONFIGURED)),
        DiagnosticLine("database_host", str(database_settings.get("HOST") or NOT_AVAILABLE)),
        DiagnosticLine("database_name", safe_database_name(database_settings.get("NAME"))),
        DiagnosticLine("database_port", str(database_settings.get("PORT") or NOT_AVAILABLE)),
        DiagnosticLine("database_vendor", connection.vendor),
        DiagnosticLine("postgresql_server_version", postgresql_server_version()),
        DiagnosticLine("database_timezone", db_timezone if db_timezone_error is None else db_timezone_error),
        DiagnosticLine("redis_url_masked", mask_url(redis_url)),
        DiagnosticLine("redis_url_fingerprint", url_fingerprint(redis_url)),
        DiagnosticLine("redis_host", redis_host(redis_url)),
        DiagnosticLine("redis_connection", f"{redis_status} ({redis_message})"),
        DiagnosticLine("latest_auctions_migration", latest_applied_migration("auctions")),
        DiagnosticLine("latest_audit_migration", latest_applied_migration("audit")),
        DiagnosticLine("git_commit_sha", git_commit_sha_from_environment()),
        DiagnosticLine("service_name", first_safe_env_value(("BIDALS_SERVICE_NAME", "SERVICE_NAME", "RENDER_SERVICE_NAME"))),
        DiagnosticLine("render_service_id", first_safe_env_value(("RENDER_SERVICE_ID",))),
        DiagnosticLine("render_service_name", first_safe_env_value(("RENDER_SERVICE_NAME", "RENDER_SERVICE_SLUG"))),
    ]


def collect_deployment_fingerprint() -> list[DiagnosticLine]:
    commands = matching_management_commands()
    return [
        DiagnosticLine("git_commit_sha", git_commit_sha()),
        DiagnosticLine("git_branch", git_branch()),
        DiagnosticLine("render_service_id", first_safe_env_value(("RENDER_SERVICE_ID",))),
        DiagnosticLine("render_service_name", first_safe_env_value(("RENDER_SERVICE_NAME", "RENDER_SERVICE_SLUG"))),
        DiagnosticLine("render_service_type", first_safe_env_value(("RENDER_SERVICE_TYPE",))),
        DiagnosticLine("render_external_hostname", first_safe_env_value(("RENDER_EXTERNAL_HOSTNAME",))),
        DiagnosticLine("service_name", first_safe_env_value(("BIDALS_SERVICE_NAME", "SERVICE_NAME", "RENDER_SERVICE_NAME"))),
        DiagnosticLine("environment", first_safe_env_value(("BIDALS_ENV", "ENV", "SENTRY_ENVIRONMENT"))),
        DiagnosticLine("app_root_path", str(settings.BASE_DIR)),
        DiagnosticLine("python_executable", sys.executable),
        DiagnosticLine("python_path", safe_python_path()),
        DiagnosticLine("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", NOT_CONFIGURED)),
        DiagnosticLine("installed_apps_audit_auctions", installed_apps_containing(("auctions", "audit"))),
        DiagnosticLine("file_staging_env_diagnostics.py", file_exists_label("staging_env_diagnostics.py")),
        DiagnosticLine("file_staging_lifecycle_readiness.py", file_exists_label("staging_lifecycle_readiness.py")),
        DiagnosticLine("matching_management_commands", ", ".join(commands) if commands else "none"),
    ]


def collect_staging_lifecycle_readiness() -> list[ReadinessLine]:
    db_timezone, db_timezone_error = database_timezone()
    migration_error = None
    try:
        applied_migrations = get_applied_migrations()
    except Exception as exc:
        applied_migrations = set()
        migration_error = exc.__class__.__name__

    counts_error = None
    try:
        counts = lifecycle_counts()
    except Exception as exc:
        counts = {}
        counts_error = exc.__class__.__name__

    return [
        bool_check("USE_TZ", settings.USE_TZ is True, f"USE_TZ={settings.USE_TZ}", "USE_TZ must be True."),
        bool_check("TIME_ZONE", is_utc_timezone(settings.TIME_ZONE), f"TIME_ZONE={settings.TIME_ZONE}", "TIME_ZONE must be UTC."),
        database_timezone_check(db_timezone, db_timezone_error),
        migration_check(
            "AUCTIONS_MIGRATION_0009",
            ("auctions", TARGET_AUCTIONS_MIGRATION) in applied_migrations,
            latest_from_applied("auctions", applied_migrations),
            TARGET_AUCTIONS_MIGRATION,
            migration_error,
        ),
        migration_check(
            "AUDIT_MIGRATION_0011",
            ("audit", TARGET_AUDIT_MIGRATION) in applied_migrations,
            latest_from_applied("audit", applied_migrations),
            TARGET_AUDIT_MIGRATION,
            migration_error,
        ),
        count_line("SCHEDULED_AUCTIONS", counts.get("scheduled_auctions"), counts_error),
        count_line("LIVE_AUCTIONS", counts.get("live_auctions"), counts_error),
        count_line("CLOSED_AUCTIONS", counts.get("closed_auctions"), counts_error),
        zero_count_check("INCONSISTENT_LOTS", counts.get("inconsistent_lots"), counts_error),
        zero_count_check("LIVE_LOTS_IN_CLOSED_AUCTIONS", counts.get("live_lots_in_closed_auctions"), counts_error),
        zero_count_check("CLOSED_LOTS_IN_LIVE_AUCTIONS", counts.get("closed_lots_in_live_auctions"), counts_error),
        zero_count_check("AUCTIONS_START_AFTER_END", counts.get("auctions_start_after_end"), counts_error),
    ]


def collect_staging_lifecycle_issue_details() -> dict:
    errors = []
    try:
        lots = [
            lot_issue_detail(lot)
            for lot in (
                Lot.objects.select_related("auction", "winner", "winning_bid")
                .annotate(bid_count=Count("bids", distinct=True))
                .filter(inconsistent_lot_query())
                .order_by("auction_id", "id")
            )
        ]
    except Exception as exc:
        lots = []
        errors.append({"section": "lot_issues", "error_type": exc.__class__.__name__})

    try:
        auctions = [
            auction_issue_detail(auction, reason="auction_start_after_end")
            for auction in Auction.objects.filter(start_time__gt=F("end_time")).order_by("id")
        ]
    except Exception as exc:
        auctions = []
        errors.append({"section": "auction_issues", "error_type": exc.__class__.__name__})

    return {
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "inconsistent_lots": sum("inconsistent_lot" in lot["reason_groups"] for lot in lots),
            "closed_lots_in_live_auctions": sum(
                "closed_lot_inside_live_auction" in lot["reasons"] for lot in lots
            ),
            "live_lots_in_closed_auctions": sum(
                "live_lot_inside_closed_auction" in lot["reasons"] for lot in lots
            ),
            "auctions_start_after_end": len(auctions),
        },
        "lot_issues": lots,
        "auction_issues": auctions,
        "errors": errors,
    }


def mask_url(value: str | None) -> str:
    parsed = parse_url_safely(value)
    if parsed is None:
        return NOT_CONFIGURED if not value else "invalid-url"

    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        return "invalid-url"

    auth = ""
    has_username = parsed.username not in (None, "")
    if has_username and parsed.password is not None:
        auth = "***:***@"
    elif parsed.password is not None:
        auth = ":***@"
    elif has_username:
        auth = "***@"

    host_display = f"[{host}]" if ":" in host and not host.startswith("[") else host
    port_display = f":{port}" if port is not None else ""
    path = safe_url_path(parsed.path)
    query = "?query=present" if parsed.query else ""
    fragment = "#fragment=present" if parsed.fragment else ""
    return f"{parsed.scheme}://{auth}{host_display}{port_display}{path}{query}{fragment}"


def url_fingerprint(value: str | None) -> str:
    parsed = parse_url_safely(value)
    if parsed is None:
        return NOT_CONFIGURED if not value else "invalid-url"

    try:
        port = parsed.port
    except ValueError:
        return "invalid-url"

    canonical = "|".join(
        (
            parsed.scheme.lower(),
            (parsed.hostname or "").lower(),
            str(port or ""),
            safe_url_path(parsed.path),
            "query=present" if parsed.query else "",
        )
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def redis_connection_status(redis_url: str | None = None) -> tuple[str, str]:
    redis_url = redis_url or getattr(settings, "REDIS_URL", "")
    if not redis_url:
        return "WARN", "REDIS_URL is not configured"

    try:
        import redis
    except ImportError:
        return "WARN", "redis package is unavailable"

    client = None
    try:
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=getattr(settings, "REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", 2.0),
            socket_timeout=getattr(settings, "REDIS_SOCKET_TIMEOUT_SECONDS", 2.0),
        )
        client.ping()
    except Exception as exc:
        return "FAIL", exc.__class__.__name__
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    return "PASS", "ping succeeded"


def database_timezone() -> tuple[str, str | None]:
    if connection.vendor != "postgresql":
        return "", f"{NOT_AVAILABLE} for {connection.vendor}"

    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW timezone")
            row = cursor.fetchone()
    except Exception as exc:
        return "", f"unavailable ({exc.__class__.__name__})"

    return str(row[0]) if row else "", None


def postgresql_server_version() -> str:
    if connection.vendor != "postgresql":
        return f"{NOT_AVAILABLE} for {connection.vendor}"

    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            row = cursor.fetchone()
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"

    return str(row[0]) if row else NOT_AVAILABLE


def latest_applied_migration(app_label: str) -> str:
    try:
        applied = get_applied_migrations()
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"
    return latest_from_applied(app_label, applied)


def get_applied_migrations() -> set[tuple[str, str]]:
    return MigrationRecorder(connection).applied_migrations()


def lifecycle_counts() -> dict[str, int]:
    live_lots_in_closed_auctions = Lot.objects.filter(
        auction__status__in=ENDED_AUCTION_STATUS_ALIASES,
        status=LotStatus.OPEN,
    ).count()
    closed_lots_in_live_auctions = Lot.objects.filter(
        auction__status__in=LIVE_AUCTION_STATUS_ALIASES,
        status__in=closed_lot_statuses(),
    ).count()
    detected_inconsistent_lots = Lot.objects.filter(inconsistent_lot_query()).count()

    return {
        "scheduled_auctions": Auction.objects.filter(status__in=SCHEDULED_AUCTION_STATUSES).count(),
        "live_auctions": Auction.objects.filter(status__in=LIVE_AUCTION_STATUS_ALIASES).count(),
        "closed_auctions": Auction.objects.filter(status__in=ENDED_AUCTION_STATUS_ALIASES).count(),
        "inconsistent_lots": detected_inconsistent_lots,
        "live_lots_in_closed_auctions": live_lots_in_closed_auctions,
        "closed_lots_in_live_auctions": closed_lots_in_live_auctions,
        "auctions_start_after_end": Auction.objects.filter(start_time__gt=F("end_time")).count(),
    }


def closed_lot_statuses() -> tuple[str, ...]:
    return (LotStatus.CLOSED, LotStatus.SOLD)


def inconsistent_lot_reason_queries() -> tuple[tuple[str, Q], ...]:
    return (
        (
            "sold_lot_missing_winner_or_winning_bid",
            Q(status=LotStatus.SOLD)
            & (
                Q(winner_id__isnull=True)
                | Q(winning_bid_id__isnull=True)
                | ~Q(winner_status=LotWinnerStatus.WINNER_ASSIGNED)
            ),
        ),
        (
            "winner_assigned_missing_winner_or_winning_bid",
            Q(winner_status=LotWinnerStatus.WINNER_ASSIGNED)
            & (Q(winner_id__isnull=True) | Q(winning_bid_id__isnull=True)),
        ),
        (
            "open_lot_has_outcome_data",
            Q(status=LotStatus.OPEN)
            & (
                Q(winner_id__isnull=False)
                | Q(winning_bid_id__isnull=False)
                | ~Q(winner_status=LotWinnerStatus.PENDING)
                | Q(winner_calculated_at__isnull=False)
            ),
        ),
        (
            "live_lot_inside_closed_auction",
            Q(auction__status__in=ENDED_AUCTION_STATUS_ALIASES, status=LotStatus.OPEN),
        ),
        (
            "closed_lot_inside_live_auction",
            Q(auction__status__in=LIVE_AUCTION_STATUS_ALIASES, status__in=closed_lot_statuses()),
        ),
    )


def inconsistent_lot_query() -> Q:
    combined = Q(pk__in=[])
    for _reason, query in inconsistent_lot_reason_queries():
        combined |= query
    return combined


def lot_issue_reasons(lot: Lot) -> list[str]:
    reasons = []
    if lot.status == LotStatus.SOLD and (
        not lot.winner_id
        or not lot.winning_bid_id
        or lot.winner_status != LotWinnerStatus.WINNER_ASSIGNED
    ):
        reasons.append("sold_lot_missing_winner_or_winning_bid")
    if lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED and (
        not lot.winner_id or not lot.winning_bid_id
    ):
        reasons.append("winner_assigned_missing_winner_or_winning_bid")
    if lot.status == LotStatus.OPEN and (
        lot.winner_id
        or lot.winning_bid_id
        or lot.winner_status != LotWinnerStatus.PENDING
        or lot.winner_calculated_at
    ):
        reasons.append("open_lot_has_outcome_data")
    if lot.auction.status in ENDED_AUCTION_STATUS_ALIASES and lot.status == LotStatus.OPEN:
        reasons.append("live_lot_inside_closed_auction")
    if lot.auction.status in LIVE_AUCTION_STATUS_ALIASES and lot.status in closed_lot_statuses():
        reasons.append("closed_lot_inside_live_auction")
    return reasons


def lot_issue_detail(lot: Lot) -> dict:
    reasons = lot_issue_reasons(lot)
    return {
        "record_type": "lot",
        "reason_groups": ["inconsistent_lot"],
        "reasons": reasons,
        "auction_id": lot.auction_id,
        "auction_title": lot.auction.title,
        "auction_status": lot.auction.status,
        "auction_effective_status": safe_effective_auction_status(lot.auction),
        "auction_start_time": iso_or_none(lot.auction.start_time),
        "auction_end_time": iso_or_none(lot.auction.end_time),
        "auction_created_at": iso_or_none(getattr(lot.auction, "created_at", None)),
        "auction_updated_at": iso_or_none(getattr(lot.auction, "updated_at", None)),
        "lot_id": lot.id,
        "lot_title": lot.title,
        "lot_status": lot.status,
        "lot_effective_status": safe_effective_lot_status(lot),
        "current_price": str(lot.current_price) if lot.current_price is not None else None,
        "winning_bid_id": lot.winning_bid_id,
        "winner_id": lot.winner_id,
        "winner_email": mask_email(getattr(lot.winner, "email", "")) if lot.winner_id else None,
        "winner_status": lot.winner_status,
        "bid_count": getattr(lot, "bid_count", None),
        "created_at": iso_or_none(getattr(lot, "created_at", None)),
        "updated_at": iso_or_none(getattr(lot, "updated_at", None)),
    }


def auction_issue_detail(auction: Auction, *, reason: str) -> dict:
    return {
        "record_type": "auction",
        "reasons": [reason],
        "auction_id": auction.id,
        "auction_title": auction.title,
        "auction_status": auction.status,
        "auction_effective_status": safe_effective_auction_status(auction),
        "auction_start_time": iso_or_none(auction.start_time),
        "auction_end_time": iso_or_none(auction.end_time),
        "auction_created_at": iso_or_none(getattr(auction, "created_at", None)),
        "auction_updated_at": iso_or_none(getattr(auction, "updated_at", None)),
        "lot_id": None,
        "lot_title": None,
        "lot_status": None,
        "lot_effective_status": None,
        "current_price": None,
        "winning_bid_id": None,
        "winner_id": None,
        "winner_email": None,
        "winner_status": None,
        "bid_count": None,
        "created_at": iso_or_none(getattr(auction, "created_at", None)),
        "updated_at": iso_or_none(getattr(auction, "updated_at", None)),
    }


def safe_effective_auction_status(auction: Auction) -> str:
    try:
        return get_effective_auction_status(auction)
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"


def safe_effective_lot_status(lot: Lot) -> str:
    try:
        return get_effective_lot_status(lot)
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"


def iso_or_none(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def mask_email(value: str | None) -> str | None:
    if not value:
        return None
    if "@" not in value:
        return "***"
    local, domain = value.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[:1]}***@{domain}"


def safe_database_name(value) -> str:
    if not value:
        return NOT_CONFIGURED
    if connection.vendor == "sqlite":
        return Path(str(value)).name
    return str(value)


def redis_host(value: str | None) -> str:
    parsed = parse_url_safely(value)
    if parsed is None:
        return NOT_CONFIGURED if not value else "invalid-url"
    return parsed.hostname or NOT_AVAILABLE


def parse_url_safely(value: str | None):
    if not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if not parsed.scheme or not parsed.hostname:
        return None
    return parsed


def safe_url_path(path: str) -> str:
    if not path:
        return ""
    if re.fullmatch(r"/[A-Za-z0-9_.-]+", path):
        return path
    return "/..."


def git_commit_sha_from_environment() -> str:
    for name in (
        "RENDER_GIT_COMMIT",
        "GIT_COMMIT_SHA",
        "GIT_COMMIT",
        "COMMIT_SHA",
        "SOURCE_COMMIT",
        "SOURCE_VERSION",
    ):
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
            return value
        return f"configured in {name}, but value is not a git SHA"
    return NOT_CONFIGURED


def git_commit_sha() -> str:
    from_env = git_commit_sha_from_environment()
    if from_env != NOT_CONFIGURED:
        return from_env
    return git_metadata("rev-parse", "--verify", "HEAD", validator=r"[0-9a-fA-F]{40}")


def git_branch() -> str:
    for name in ("RENDER_GIT_BRANCH", "GIT_BRANCH", "BRANCH", "SOURCE_BRANCH"):
        value = os.environ.get(name, "").strip()
        if value:
            return safe_env_value(value)
    return git_metadata("branch", "--show-current")


def git_metadata(*args: str, validator: str | None = None) -> str:
    candidate_roots = (getattr(settings, "ROOT_DIR", settings.BASE_DIR), settings.BASE_DIR)
    for root in candidate_roots:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=root,
                capture_output=True,
                check=False,
                text=True,
                timeout=2,
            )
        except Exception:
            continue

        value = result.stdout.strip()
        if result.returncode != 0 or not value:
            continue
        if validator and not re.fullmatch(validator, value):
            continue
        return safe_env_value(value)
    return NOT_CONFIGURED


def first_safe_env_value(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return safe_env_value(value)
    return NOT_CONFIGURED


def safe_env_value(value: str) -> str:
    if len(value) > 160:
        return "configured, but value is too long to print safely"
    if not re.fullmatch(r"[A-Za-z0-9_.:/@ -]+", value):
        return "configured, but value contains characters not printed safely"
    return value


def command_file_path(filename: str) -> Path:
    return settings.BASE_DIR / "apps" / "audit" / "management" / "commands" / filename


def file_exists_label(filename: str) -> str:
    path = command_file_path(filename)
    return f"{path.exists()} ({path})"


def matching_management_commands() -> list[str]:
    command_names = sorted(get_commands())
    return [
        name
        for name in command_names
        if any(term in name.lower() for term in COMMAND_FILTER_TERMS)
    ]


def installed_apps_containing(terms: tuple[str, ...]) -> str:
    matches = [
        app
        for app in settings.INSTALLED_APPS
        if any(term in app.lower() for term in terms)
    ]
    return ", ".join(matches) if matches else "none"


def safe_python_path() -> str:
    paths = [safe_path_value(path) for path in sys.path if path]
    return os.pathsep.join(paths) if paths else NOT_CONFIGURED


def safe_path_value(value: str) -> str:
    if len(value) > 240:
        return "<path too long>"
    if not re.fullmatch(r"[A-Za-z0-9_./:\\ -]+", value):
        return "<path contains unsafe characters>"
    return value


def bool_check(name: str, passed: bool, pass_message: str, fail_message: str) -> ReadinessLine:
    if passed:
        return ReadinessLine("PASS", name, pass_message)
    return ReadinessLine("FAIL", name, fail_message)


def database_timezone_check(value: str, error: str | None) -> ReadinessLine:
    if error is not None:
        return ReadinessLine("WARN", "DATABASE_TIMEZONE", error)
    if is_utc_timezone(value):
        return ReadinessLine("PASS", "DATABASE_TIMEZONE", f"timezone={value}")
    return ReadinessLine("FAIL", "DATABASE_TIMEZONE", f"timezone={value or NOT_AVAILABLE}; expected UTC")


def migration_check(name: str, applied: bool, latest: str, target: str, error: str | None = None) -> ReadinessLine:
    if error is not None:
        return ReadinessLine("FAIL", name, f"could not inspect migrations ({error})")
    if applied:
        return ReadinessLine("PASS", name, f"{target} is applied; latest={latest}")
    return ReadinessLine("FAIL", name, f"{target} is not applied; latest={latest}")


def latest_from_applied(app_label: str, applied: set[tuple[str, str]]) -> str:
    names = sorted(name for app, name in applied if app == app_label)
    return names[-1] if names else "none"


def count_line(name: str, count: int | None, error: str | None) -> ReadinessLine:
    if error is not None:
        return ReadinessLine("FAIL", name, f"unavailable ({error})")
    return ReadinessLine("PASS", name, f"count={count}")


def zero_count_check(name: str, count: int | None, error: str | None = None) -> ReadinessLine:
    if error is not None:
        return ReadinessLine("FAIL", name, f"unavailable ({error})")
    if count == 0:
        return ReadinessLine("PASS", name, "count=0")
    return ReadinessLine("FAIL", name, f"count={count}")


def is_utc_timezone(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"utc", "etc/utc", "posix/utc", "z"}
