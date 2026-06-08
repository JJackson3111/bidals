from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from bidals.storage import build_s3_storage_options
from bidals.settings.origins import configured_origins
from bidals.settings.validation import RATE_LIMIT_DEFAULTS, validate_rate_limit_cache_failure_mode, validate_rate_limit_settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    ENABLE_STRUCTURED_LOGGING=(bool, True),
)

env_file = ROOT_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-secret-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper()
ENABLE_STRUCTURED_LOGGING = env.bool("ENABLE_STRUCTURED_LOGGING", default=True)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts",
    "apps.auctions",
    "apps.raffles",
    "apps.audit",
    "apps.leads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "bidals.logging.RequestLogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.audit.security.SecurityHeadersMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bidals.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bidals.wsgi.application"

DATABASE_URL_VALUE = env("DATABASE_URL", default=env("DJANGO_DATABASE_URL", default=""))
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=DATABASE_URL_VALUE or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
LOT_IMAGE_MAX_UPLOAD_SIZE_MB = env.int("LOT_IMAGE_MAX_UPLOAD_SIZE_MB", default=5)
SERVE_LOCAL_MEDIA = env.bool("SERVE_LOCAL_MEDIA", default=DEBUG)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    INSTALLED_APPS.append("storages")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", default="path")
    AWS_S3_SIGNATURE_VERSION = env("AWS_S3_SIGNATURE_VERSION", default="s3v4")
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=not bool(AWS_S3_CUSTOM_DOMAIN))
    AWS_S3_CACHE_CONTROL = env("AWS_S3_CACHE_CONTROL", default="max-age=86400")
    S3_STORAGE_OPTIONS = build_s3_storage_options(
        {
            "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
            "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
            "AWS_STORAGE_BUCKET_NAME": AWS_STORAGE_BUCKET_NAME,
            "AWS_S3_REGION_NAME": AWS_S3_REGION_NAME,
            "AWS_S3_ENDPOINT_URL": AWS_S3_ENDPOINT_URL,
            "AWS_S3_CUSTOM_DOMAIN": AWS_S3_CUSTOM_DOMAIN,
            "AWS_S3_ADDRESSING_STYLE": AWS_S3_ADDRESSING_STYLE,
            "AWS_S3_SIGNATURE_VERSION": AWS_S3_SIGNATURE_VERSION,
            "AWS_QUERYSTRING_AUTH": AWS_QUERYSTRING_AUTH,
            "AWS_S3_OBJECT_PARAMETERS": {"CacheControl": AWS_S3_CACHE_CONTROL},
        }
    )
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": S3_STORAGE_OPTIONS,
    }
    if S3_STORAGE_OPTIONS.get("custom_domain"):
        MEDIA_URL = f"https://{S3_STORAGE_OPTIONS['custom_domain']}/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "EXCEPTION_HANDLER": "apps.audit.security.security_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": env.bool("JWT_ROTATE_REFRESH_TOKENS", default=True),
    "BLACKLIST_AFTER_ROTATION": env.bool("JWT_BLACKLIST_AFTER_ROTATION", default=True),
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="development" if DEBUG else "production")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:
        raise ImproperlyConfigured("SENTRY_DSN is configured but sentry-sdk is not installed.") from exc

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )

CORS_ALLOWED_ORIGINS = configured_origins(
    env,
    ("DJANGO_CORS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)
CSRF_TRUSTED_ORIGINS = configured_origins(
    env,
    ("DJANGO_CSRF_TRUSTED_ORIGINS", "CSRF_TRUSTED_ORIGINS"),
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=False)
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = env.float("REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", default=2.0)
REDIS_SOCKET_TIMEOUT_SECONDS = env.float("REDIS_SOCKET_TIMEOUT_SECONDS", default=2.0)
REDIS_CACHE_KEY_PREFIX = env("REDIS_CACHE_KEY_PREFIX", default="bidals")
REDIS_CACHE_OPTIONS = {
    "socket_connect_timeout": REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
    "socket_timeout": REDIS_SOCKET_TIMEOUT_SECONDS,
}

if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": REDIS_CACHE_KEY_PREFIX,
            "OPTIONS": REDIS_CACHE_OPTIONS,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "bidals-local-cache",
        }
    }

BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS = env.int("BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS", default=10)
BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS = env.int("BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS", default=2)
BID_RATE_LIMIT_WINDOW_SECONDS = env.int("BID_RATE_LIMIT_WINDOW_SECONDS", default=60)
ENABLE_RATE_LIMITING = env.bool("ENABLE_RATE_LIMITING", default=True)
RATE_LIMIT_CACHE_FAILURE_MODE = validate_rate_limit_cache_failure_mode(
    env("RATE_LIMIT_CACHE_FAILURE_MODE", default="deny")
)
RATE_LIMIT_LOGIN = env("RATE_LIMIT_LOGIN", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_LOGIN"])
RATE_LIMIT_REGISTRATION = env("RATE_LIMIT_REGISTRATION", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_REGISTRATION"])
RATE_LIMIT_BID_CREATE = env("RATE_LIMIT_BID_CREATE", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_BID_CREATE"])
RATE_LIMIT_PASSWORD_RESET = env("RATE_LIMIT_PASSWORD_RESET", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_PASSWORD_RESET"])
RATE_LIMIT_ADMIN_ACTIONS = env("RATE_LIMIT_ADMIN_ACTIONS", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_ADMIN_ACTIONS"])
RATE_LIMIT_LEAD_REQUESTS = env("RATE_LIMIT_LEAD_REQUESTS", default=RATE_LIMIT_DEFAULTS["RATE_LIMIT_LEAD_REQUESTS"])
validate_rate_limit_settings(
    {
        "RATE_LIMIT_LOGIN": RATE_LIMIT_LOGIN,
        "RATE_LIMIT_REGISTRATION": RATE_LIMIT_REGISTRATION,
        "RATE_LIMIT_BID_CREATE": RATE_LIMIT_BID_CREATE,
        "RATE_LIMIT_PASSWORD_RESET": RATE_LIMIT_PASSWORD_RESET,
        "RATE_LIMIT_ADMIN_ACTIONS": RATE_LIMIT_ADMIN_ACTIONS,
        "RATE_LIMIT_LEAD_REQUESTS": RATE_LIMIT_LEAD_REQUESTS,
    }
)
BID_ANOMALY_REJECT_THRESHOLD = env.int("BID_ANOMALY_REJECT_THRESHOLD", default=5)
BID_ANOMALY_RATE_LIMIT_THRESHOLD = env.int("BID_ANOMALY_RATE_LIMIT_THRESHOLD", default=3)

ALERT_WEBHOOK_URL = env("ALERT_WEBHOOK_URL", default="")
ALERT_WEBHOOK_TIMEOUT_SECONDS = env.int("ALERT_WEBHOOK_TIMEOUT_SECONDS", default=3)

EMAIL_NOTIFICATIONS_ENABLED = env.bool("EMAIL_NOTIFICATIONS_ENABLED", default=False)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = env("DJANGO_REFERRER_POLICY", default="same-origin")
PERMISSIONS_POLICY = env(
    "DJANGO_PERMISSIONS_POLICY",
    default="camera=(), microphone=(), geolocation=(), payment=()",
)
CONTENT_SECURITY_POLICY = env("DJANGO_CONTENT_SECURITY_POLICY", default="")
CONTENT_SECURITY_POLICY_REPORT_ONLY = env.bool("DJANGO_CONTENT_SECURITY_POLICY_REPORT_ONLY", default=True)

_LOG_FORMATTER = "json" if ENABLE_STRUCTURED_LOGGING else "plain"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "bidals.logging.JsonFormatter",
        },
        "plain": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": _LOG_FORMATTER,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "bidals.requests": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
