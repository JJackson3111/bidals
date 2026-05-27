from .base import *  # noqa: F403
from .base import env
from .validation import validate_rate_limit_cache_failure_mode

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "backend"]
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="development")
RATE_LIMIT_CACHE_FAILURE_MODE = validate_rate_limit_cache_failure_mode(
    env("RATE_LIMIT_CACHE_FAILURE_MODE", default="allow")
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
