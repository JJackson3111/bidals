from .base import *  # noqa: F403
from .base import REDIS_CACHE_KEY_PREFIX, REDIS_CACHE_OPTIONS, REDIS_URL, env
from .validation import assert_required_production_env
from django.core.exceptions import ImproperlyConfigured

assert_required_production_env()

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

FRONTEND_URL = env("FRONTEND_URL", default="")
CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=[FRONTEND_URL] if FRONTEND_URL else [],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[FRONTEND_URL] if FRONTEND_URL else [],
)
if "*" in CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("DJANGO_CORS_ALLOWED_ORIGINS cannot contain '*' in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = env.bool("DJANGO_CSRF_COOKIE_HTTPONLY", default=True)
SESSION_COOKIE_SAMESITE = env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("DJANGO_CSRF_COOKIE_SAMESITE", default="Lax")
SECURE_REFERRER_POLICY = env("DJANGO_REFERRER_POLICY", default="same-origin")

USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=True)
if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": REDIS_CACHE_KEY_PREFIX,
            "OPTIONS": REDIS_CACHE_OPTIONS,
        }
    }
