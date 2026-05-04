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
