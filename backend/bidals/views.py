from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "service": "bidals-backend"})


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    if getattr(settings, "USE_REDIS_CACHE", False):
        try:
            key = "readiness-check"
            cache.set(key, "ok", timeout=10)
            checks["cache"] = "ok" if cache.get(key) == "ok" else "error"
            cache.delete(key)
        except Exception:
            checks["cache"] = "error"
    else:
        checks["cache"] = "skipped"

    ready = all(value in {"ok", "skipped"} for value in checks.values())
    return Response(
        {
            "status": "ok" if ready else "degraded",
            "service": "bidals-backend",
            "checks": checks,
        },
        status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
