from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

RATE_LIMIT_SETTINGS = (
    "RATE_LIMIT_LOGIN",
    "RATE_LIMIT_REGISTRATION",
    "RATE_LIMIT_BID_CREATE",
    "RATE_LIMIT_PASSWORD_RESET",
    "RATE_LIMIT_ADMIN_ACTIONS",
    "RATE_LIMIT_LEAD_REQUESTS",
)
RATE_LIMIT_DEFAULTS = {
    "RATE_LIMIT_LOGIN": "5/minute",
    "RATE_LIMIT_REGISTRATION": "5/minute",
    "RATE_LIMIT_BID_CREATE": "",
    "RATE_LIMIT_PASSWORD_RESET": "3/hour",
    "RATE_LIMIT_ADMIN_ACTIONS": "30/minute",
    "RATE_LIMIT_LEAD_REQUESTS": "3/hour",
}
RATE_LIMIT_CACHE_FAILURE_MODES = {"allow", "deny"}


def missing_required_production_env() -> list[str]:
    missing: list[str] = []

    for name in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS"):
        if not _env_value(name):
            missing.append(name)

    if not (_env_value("DATABASE_URL") or _env_value("DJANGO_DATABASE_URL")):
        missing.append("DATABASE_URL or DJANGO_DATABASE_URL")

    if not (
        _env_value("FRONTEND_URL")
        or _env_value("DJANGO_CORS_ALLOWED_ORIGINS")
        or _env_value("CORS_ALLOWED_ORIGINS")
    ):
        missing.append("FRONTEND_URL or DJANGO_CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGINS")

    if not (
        _env_value("FRONTEND_URL")
        or _env_value("DJANGO_CSRF_TRUSTED_ORIGINS")
        or _env_value("CSRF_TRUSTED_ORIGINS")
    ):
        missing.append("FRONTEND_URL or DJANGO_CSRF_TRUSTED_ORIGINS or CSRF_TRUSTED_ORIGINS")

    return missing


def assert_required_production_env() -> None:
    missing = missing_required_production_env()
    if missing:
        raise ImproperlyConfigured(
            "Production settings require these environment variables: "
            + ", ".join(missing)
            + "."
        )


def validate_rate_limit_settings(values: dict[str, str | int | None]) -> None:
    invalid: list[str] = []
    for name in RATE_LIMIT_SETTINGS:
        raw_value = values[name] if name in values else RATE_LIMIT_DEFAULTS[name]
        if name == "RATE_LIMIT_BID_CREATE" and not str(raw_value or "").strip():
            continue

        try:
            parse_rate_limit(raw_value, setting_name=name)
        except (TypeError, ValueError):
            invalid.append(name)

    if invalid:
        raise ImproperlyConfigured(
            "Invalid rate-limit environment value(s): "
            + ", ".join(invalid)
            + ". Use formats like '5/minute', '30/hour', or a positive integer per minute."
        )


def validate_rate_limit_cache_failure_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode not in RATE_LIMIT_CACHE_FAILURE_MODES:
        raise ImproperlyConfigured(
            "RATE_LIMIT_CACHE_FAILURE_MODE must be one of: "
            + ", ".join(sorted(RATE_LIMIT_CACHE_FAILURE_MODES))
            + "."
        )
    return mode


def parse_rate_limit(value: str | int | None, *, setting_name: str = "rate limit") -> tuple[int, int]:
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"{setting_name} must be positive.")
        return value, 60

    raw = str(value or "").strip().lower()
    if raw.isdigit():
        amount = int(raw)
        if amount <= 0:
            raise ValueError(f"{setting_name} must be positive.")
        return amount, 60

    if "/" not in raw:
        raise ValueError(f"Invalid {setting_name}: {value!r}. Use a format like '5/minute'.")

    amount_text, period_text = raw.split("/", 1)
    try:
        amount = int(amount_text)
    except ValueError as exc:
        raise ValueError(f"Invalid {setting_name} amount: {amount_text!r}.") from exc
    if amount <= 0:
        raise ValueError(f"{setting_name} must be positive.")

    period_text = period_text.strip()
    seconds_by_period = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
    }
    if period_text not in seconds_by_period:
        raise ValueError(f"Invalid {setting_name} period: {period_text!r}.")
    return amount, seconds_by_period[period_text]


def _env_value(name: str) -> str:
    return os.environ.get(name, "").strip()
