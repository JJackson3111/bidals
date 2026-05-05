from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


REQUIRED_S3_SETTINGS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_STORAGE_BUCKET_NAME",
    "AWS_S3_ENDPOINT_URL",
    "AWS_S3_REGION_NAME",
)


def validate_s3_settings(values: dict[str, str | None]) -> None:
    missing = [name for name in REQUIRED_S3_SETTINGS if not values.get(name)]
    if missing:
        required = ", ".join(missing)
        raise ImproperlyConfigured(
            f"USE_S3=True requires Cloudflare R2/S3-compatible storage settings: {required}."
        )

    endpoint = str(values["AWS_S3_ENDPOINT_URL"]).strip()
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ImproperlyConfigured("AWS_S3_ENDPOINT_URL must be a full HTTPS endpoint URL.")


def normalize_storage_domain(value: str | None) -> str:
    raw_value = (value or "").strip().rstrip("/")
    if not raw_value:
        return ""

    parsed = urlparse(raw_value if "://" in raw_value else f"https://{raw_value}")
    if parsed.scheme != "https" or not parsed.netloc:
        raise ImproperlyConfigured("AWS_S3_CUSTOM_DOMAIN must be a hostname or HTTPS URL.")
    return f"{parsed.netloc}{parsed.path}".strip("/")


def _as_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def build_s3_storage_options(values: dict[str, str | bool | dict | None]) -> dict:
    validate_s3_settings(values)
    custom_domain = normalize_storage_domain(str(values.get("AWS_S3_CUSTOM_DOMAIN") or ""))

    options = {
        "access_key": values["AWS_ACCESS_KEY_ID"],
        "secret_key": values["AWS_SECRET_ACCESS_KEY"],
        "bucket_name": values["AWS_STORAGE_BUCKET_NAME"],
        "endpoint_url": values["AWS_S3_ENDPOINT_URL"],
        "region_name": values["AWS_S3_REGION_NAME"],
        "signature_version": values.get("AWS_S3_SIGNATURE_VERSION") or "s3v4",
        "addressing_style": values.get("AWS_S3_ADDRESSING_STYLE") or "path",
        "querystring_auth": _as_bool(values.get("AWS_QUERYSTRING_AUTH")),
        "file_overwrite": False,
        "default_acl": None,
        "object_parameters": values.get("AWS_S3_OBJECT_PARAMETERS") or {},
    }
    if custom_domain:
        options["custom_domain"] = custom_domain
    return options
