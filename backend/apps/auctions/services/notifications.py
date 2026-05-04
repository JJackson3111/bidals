import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, NotificationStatus, OutboundNotification

logger = logging.getLogger(__name__)


def emit_notification_event(*, event_type: str, recipient, entity_type: str, entity_id: str, metadata: dict | None = None) -> OutboundNotification:
    """Queue an informational notification event without making it authoritative."""
    metadata = metadata or {}
    server_timestamp = timezone.now()
    subject, body = _build_notification_content(
        event_type=event_type,
        recipient=recipient,
        entity_type=entity_type,
        entity_id=str(entity_id),
        metadata=metadata,
    )
    notification = OutboundNotification.objects.create(
        recipient=recipient,
        recipient_email=getattr(recipient, "email", "") or "",
        notification_type=event_type,
        subject=subject,
        body=body,
        related_entity_type=entity_type,
        related_entity_id=str(entity_id),
        metadata=metadata,
    )
    AuditLog.objects.create(
        actor=recipient,
        action=AuditAction.NOTIFICATION_EVENT,
        entity_type=entity_type,
        entity_id=str(entity_id),
        server_timestamp=server_timestamp,
        metadata={
            "event_type": event_type,
            "notification_id": notification.id,
            "recipient_id": recipient.id if recipient else None,
            "delivery_status": NotificationStatus.PENDING,
            **metadata,
        },
    )
    logger.info(
        "Notification event recorded",
        extra={
            "event": "notification_event",
            "notification_event_type": event_type,
            "notification_id": notification.id,
            "recipient_id": recipient.id if recipient else None,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "delivery_status": NotificationStatus.PENDING,
        },
    )
    return notification


def deliver_pending_notifications(*, limit: int = 50) -> dict:
    pending = list(
        OutboundNotification.objects.select_related("recipient")
        .filter(status=NotificationStatus.PENDING)
        .order_by("created_at", "id")[:limit]
    )
    result = {"seen": len(pending), "sent": 0, "skipped": 0, "failed": 0}

    for notification in pending:
        if _should_skip_delivery(notification):
            _mark_notification(
                notification,
                status=NotificationStatus.SKIPPED,
                error_message="Email notifications are disabled or email configuration is incomplete.",
            )
            result["skipped"] += 1
            continue

        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient_email],
                fail_silently=False,
            )
        except Exception as exc:
            _mark_notification(
                notification,
                status=NotificationStatus.FAILED,
                error_message=f"{type(exc).__name__}: {str(exc)[:400]}",
            )
            result["failed"] += 1
            logger.exception(
                "Notification delivery failed",
                extra={
                    "event": "notification_delivery_failed",
                    "notification_id": notification.id,
                    "notification_type": notification.notification_type,
                    "error_type": type(exc).__name__,
                },
            )
            continue

        _mark_notification(notification, status=NotificationStatus.SENT)
        result["sent"] += 1

    logger.info(
        "Notification delivery run completed",
        extra={
            "event": "notification_delivery_run",
            **result,
        },
    )
    return result


def _should_skip_delivery(notification: OutboundNotification) -> bool:
    return not (
        getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False)
        and getattr(settings, "DEFAULT_FROM_EMAIL", "")
        and notification.recipient_email
    )


def _mark_notification(notification: OutboundNotification, *, status: str, error_message: str = "") -> None:
    notification.status = status
    notification.error_message = error_message
    if status == NotificationStatus.SENT:
        notification.sent_at = timezone.now()
    notification.save(update_fields=("status", "sent_at", "error_message"))

    AuditLog.objects.create(
        actor=notification.recipient,
        action=AuditAction.NOTIFICATION_EVENT,
        entity_type=notification.related_entity_type,
        entity_id=notification.related_entity_id,
        metadata={
            "event_type": "notification_delivery",
            "notification_id": notification.id,
            "notification_type": notification.notification_type,
            "delivery_status": status,
            "error_message": error_message,
        },
    )
    log_method = logger.warning if status in {NotificationStatus.SKIPPED, NotificationStatus.FAILED} else logger.info
    log_method(
        "Notification delivery status updated",
        extra={
            "event": "notification_delivery",
            "notification_id": notification.id,
            "notification_type": notification.notification_type,
            "delivery_status": status,
        },
    )


def _build_notification_content(*, event_type: str, recipient, entity_type: str, entity_id: str, metadata: dict) -> tuple[str, str]:
    if event_type == "winner_assigned":
        subject = "BIDALS winner confirmation"
        body = (
            "You have the winning bid on a BIDALS lot.\n\n"
            f"Lot ID: {metadata.get('lot_id', entity_id)}\n"
            f"Auction ID: {metadata.get('auction_id', 'unknown')}\n"
            f"Winning bid ID: {metadata.get('winning_bid_id', 'unknown')}\n"
            f"Amount: {metadata.get('amount', 'unknown')}\n\n"
            "This message is informational. The backend auction record remains the source of truth."
        )
        return subject, body

    if event_type == "auction_ended":
        subject = "BIDALS auction ended"
        body = (
            "A BIDALS auction you manage has ended and winner calculation has run.\n\n"
            f"Auction ID: {metadata.get('auction_id', entity_id)}\n"
            f"Lots processed: {metadata.get('lots_processed', 'unknown')}\n\n"
            "Review final outcomes in the seller dashboard."
        )
        return subject, body

    fulfillment_messages = {
        "winner_confirmed": (
            "BIDALS winner confirmed",
            "Your winning lot has been confirmed by the seller or admin.",
        ),
        "seller_contacted": (
            "BIDALS seller contacted",
            "The seller has recorded that follow-up has started for your winning lot.",
        ),
        "awaiting_collection_or_delivery": (
            "BIDALS fulfillment update",
            "Your winning lot is awaiting collection or delivery arrangements.",
        ),
        "fulfillment_completed": (
            "BIDALS fulfillment completed",
            "Fulfillment has been marked complete for your winning lot.",
        ),
        "fulfillment_cancelled": (
            "BIDALS fulfillment cancelled",
            "Fulfillment has been marked cancelled for your winning lot.",
        ),
        "fulfillment_disputed": (
            "BIDALS fulfillment needs review",
            "Fulfillment has been marked disputed for your winning lot.",
        ),
    }
    if event_type in fulfillment_messages:
        subject, intro = fulfillment_messages[event_type]
        body = (
            f"{intro}\n\n"
            f"Lot ID: {metadata.get('lot_id', 'unknown')}\n"
            f"Auction ID: {metadata.get('auction_id', 'unknown')}\n"
            f"Fulfillment status: {metadata.get('status', 'unknown')}\n\n"
            "This message is informational. BIDALS backend records remain the source of truth."
        )
        return subject, body

    if event_type == "outcome_repair_applied":
        subject = "BIDALS outcome correction applied"
        body = (
            "An admin-reviewed outcome correction has been applied to a BIDALS lot.\n\n"
            f"Lot ID: {metadata.get('lot_id', entity_id)}\n"
            f"Auction ID: {metadata.get('auction_id', 'unknown')}\n"
            f"Winning bid ID: {metadata.get('winning_bid_id', 'unknown')}\n\n"
            "This message is informational. BIDALS backend records remain the source of truth."
        )
        return subject, body

    subject = f"BIDALS notification: {event_type}"
    body = (
        f"Notification type: {event_type}\n"
        f"Related entity: {entity_type}:{entity_id}\n\n"
        "This message is informational. Backend records remain the source of truth."
    )
    return subject, body
