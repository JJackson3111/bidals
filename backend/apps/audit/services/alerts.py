from dataclasses import dataclass
import json
import logging
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertResult:
    delivered: bool
    delivery_status: str
    audit_log_id: int


def send_alert(*, event_type: str, severity: str, message: str, metadata: dict | None = None) -> AlertResult:
    metadata = metadata or {}
    server_timestamp = timezone.now()
    payload = {
        "service": "bidals",
        "event_type": event_type,
        "severity": severity,
        "message": message,
        "metadata": metadata,
        "server_timestamp": server_timestamp.isoformat(),
    }

    webhook_url = getattr(settings, "ALERT_WEBHOOK_URL", "")
    delivery_status = "not_configured"
    delivered = False

    if webhook_url:
        try:
            request = Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "bidals-alert-hook/1.0"},
                method="POST",
            )
            with urlopen(request, timeout=getattr(settings, "ALERT_WEBHOOK_TIMEOUT_SECONDS", 3)) as response:
                delivered = 200 <= response.status < 300
                delivery_status = "delivered" if delivered else f"http_{response.status}"
        except Exception as exc:
            delivery_status = "failed"
            logger.exception(
                "Alert webhook delivery failed",
                extra={
                    "event": "alert_hook_failed",
                    "alert_event_type": event_type,
                    "severity": severity,
                    "error_type": type(exc).__name__,
                },
            )

    audit = AuditLog.objects.create(
        actor=None,
        action=AuditAction.ALERT_TRIGGERED,
        entity_type="alert",
        entity_id=event_type,
        server_timestamp=server_timestamp,
        metadata={
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "delivery_status": delivery_status,
            "delivered": delivered,
            **metadata,
        },
    )

    logger.warning(
        "Alert triggered",
        extra={
            "event": "alert_triggered",
            "alert_event_type": event_type,
            "severity": severity,
            "delivery_status": delivery_status,
            "delivered": delivered,
        },
    )
    return AlertResult(delivered=delivered, delivery_status=delivery_status, audit_log_id=audit.id)
