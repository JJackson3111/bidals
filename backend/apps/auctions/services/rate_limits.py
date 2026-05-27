from dataclasses import dataclass
import logging
import time

from django.conf import settings
from django.core.cache import cache

from apps.audit.security import parse_rate, rate_limit_cache_failure_allows_requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BidRateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    scope: str
    key: str
    cache_available: bool = True


def check_bid_rate_limit(request) -> BidRateLimitResult:
    user = request.user
    if not getattr(settings, "ENABLE_RATE_LIMITING", True):
        return BidRateLimitResult(
            allowed=True,
            limit=0,
            remaining=0,
            retry_after=0,
            scope="disabled",
            key="disabled",
        )

    window_seconds = int(getattr(settings, "BID_RATE_LIMIT_WINDOW_SECONDS", 60))

    if user and user.is_authenticated:
        scope = "user"
        identifier = str(user.id)
        limit = int(getattr(settings, "BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS", 10))
    else:
        scope = "anonymous"
        identifier = _client_ip(request)
        limit = int(getattr(settings, "BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS", 2))

    configured_rate = getattr(settings, "RATE_LIMIT_BID_CREATE", "")
    if configured_rate:
        limit, window_seconds = parse_rate(configured_rate)

    now = time.time()
    bucket = int(now // window_seconds)
    retry_after = max(1, window_seconds - int(now % window_seconds))
    key = f"bidals:bid-rate:{scope}:{identifier}:{bucket}"

    try:
        count = _increment_key(key, timeout=window_seconds + 5)
    except Exception as exc:
        allow_request = rate_limit_cache_failure_allows_requests()
        logger.warning(
            "Bid rate-limit cache unavailable; %s bid attempt",
            "allowing" if allow_request else "denying",
            extra={
                "event": "bid_rate_limit_cache_unavailable",
                "scope": scope,
                "key": key,
                "error_type": type(exc).__name__,
                "failure_mode": getattr(settings, "RATE_LIMIT_CACHE_FAILURE_MODE", "deny"),
            },
        )
        return BidRateLimitResult(
            allowed=allow_request,
            limit=limit,
            remaining=limit if allow_request else 0,
            retry_after=0 if allow_request else window_seconds,
            scope=scope,
            key=key,
            cache_available=False,
        )

    remaining = max(0, limit - count)

    return BidRateLimitResult(
        allowed=count <= limit,
        limit=limit,
        remaining=remaining,
        retry_after=retry_after,
        scope=scope,
        key=key,
    )


def _increment_key(key: str, *, timeout: int) -> int:
    if cache.add(key, 1, timeout=timeout):
        return 1

    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.META.get("REMOTE_ADDR", "unknown")
