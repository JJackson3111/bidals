from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.audit.models import AuditAction, AuditLog
from apps.audit.safety import sanitize_metadata
from bidals.settings.validation import parse_rate_limit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitCheck:
    allowed: bool
    scope: str
    limit: int
    window_seconds: int
    retry_after: int
    remaining: int
    cache_available: bool = True


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        permissions_policy = getattr(settings, "PERMISSIONS_POLICY", "")
        if permissions_policy:
            if "Permissions-Policy" not in response:
                response["Permissions-Policy"] = permissions_policy

        content_security_policy = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if content_security_policy:
            header_name = (
                "Content-Security-Policy-Report-Only"
                if getattr(settings, "CONTENT_SECURITY_POLICY_REPORT_ONLY", True)
                else "Content-Security-Policy"
            )
            if header_name not in response:
                response[header_name] = content_security_policy
        return response


def request_audit_metadata(request, extra: dict | None = None) -> dict:
    user = getattr(request, "user", None)
    metadata = {
        "request_id": getattr(request, "request_id", None),
        "request_path": getattr(request, "path", ""),
        "request_method": getattr(request, "method", ""),
        "client_ip": client_ip(request),
        "user_agent": (request.META.get("HTTP_USER_AGENT", "") if request else "")[:240],
        "actor_id": user.id if getattr(user, "is_authenticated", False) else None,
        "actor_role": getattr(user, "role", "") if getattr(user, "is_authenticated", False) else "",
    }
    if extra:
        metadata.update(extra)
    return sanitize_metadata(metadata)


def audit_security_event(
    *,
    request=None,
    actor=None,
    action: str,
    entity_type: str = "security",
    entity_id: str = "request",
    metadata: dict | None = None,
) -> AuditLog | None:
    actor_obj = actor if getattr(actor, "is_authenticated", False) else None
    event_metadata = request_audit_metadata(request, metadata or {}) if request is not None else sanitize_metadata(metadata or {})
    if actor_obj is not None:
        event_metadata["actor_id"] = actor_obj.id
        event_metadata["actor_role"] = getattr(actor_obj, "role", "")

    try:
        return AuditLog.objects.create(
            actor=actor_obj,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            server_timestamp=timezone.now(),
            metadata=event_metadata,
        )
    except Exception:
        logger.exception(
            "security_audit_log_failed",
            extra={
                "event": "security_audit_log_failed",
                "action": str(action),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
            },
        )
        return None


def check_security_rate_limit(
    request,
    *,
    scope: str,
    identifier: str,
    setting_name: str,
    default_rate: str,
    actor=None,
) -> RateLimitCheck:
    if not getattr(settings, "ENABLE_RATE_LIMITING", True):
        limit, window_seconds = parse_rate(default_rate)
        return RateLimitCheck(
            allowed=True,
            scope=scope,
            limit=limit,
            window_seconds=window_seconds,
            retry_after=0,
            remaining=limit,
        )

    rate_value = getattr(settings, setting_name, default_rate)
    limit, window_seconds = parse_rate(rate_value)
    retry_after = window_seconds
    key = f"bidals:security-rate:{scope}:{_safe_identifier(identifier)}"

    try:
        count = _increment_key(key, timeout=window_seconds + 5)
    except Exception as exc:
        logger.warning(
            "Security rate-limit cache unavailable; allowing request",
            extra={
                "event": "security_rate_limit_cache_unavailable",
                "scope": scope,
                "setting_name": setting_name,
                "error_type": type(exc).__name__,
            },
        )
        return RateLimitCheck(
            allowed=True,
            scope=scope,
            limit=limit,
            window_seconds=window_seconds,
            retry_after=0,
            remaining=limit,
            cache_available=False,
        )

    remaining = max(0, limit - count)
    allowed = count <= limit
    result = RateLimitCheck(
        allowed=allowed,
        scope=scope,
        limit=limit,
        window_seconds=window_seconds,
        retry_after=retry_after,
        remaining=remaining,
    )

    if not allowed:
        audit_security_event(
            request=request,
            actor=actor,
            action=AuditAction.RATE_LIMIT_TRIGGERED,
            entity_type="rate_limit",
            entity_id=scope,
            metadata={
                "scope": scope,
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            },
        )
    return result


def rate_limited_response(result: RateLimitCheck) -> Response:
    response = Response(
        {
            "detail": "Too many requests. Please wait before trying again.",
            "reason": "RATE_LIMITED",
            "scope": result.scope,
            "retry_after": result.retry_after,
        },
        status=429,
    )
    response["Retry-After"] = str(result.retry_after)
    return response


def security_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None and response.status_code in {401, 403}:
        request = context.get("request")
        user = getattr(request, "user", None) if request is not None else None
        audit_security_event(
            request=request,
            actor=user if getattr(user, "is_authenticated", False) else None,
            action=AuditAction.PERMISSION_DENIED,
            entity_type="request",
            entity_id=getattr(request, "path", "unknown") if request is not None else "unknown",
            metadata={
                "status_code": response.status_code,
                "view": context.get("view").__class__.__name__ if context.get("view") else "",
            },
        )
    return response


def client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown") if request else "unknown"


def parse_rate(value: str | int) -> tuple[int, int]:
    return parse_rate_limit(value)


def _increment_key(key: str, *, timeout: int) -> int:
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def _safe_identifier(identifier: str) -> str:
    return hashlib.sha256(str(identifier).encode("utf-8")).hexdigest()[:32]
