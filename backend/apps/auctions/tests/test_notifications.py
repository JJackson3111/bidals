from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, NotificationStatus, OutboundNotification
from apps.auctions.services.notifications import deliver_pending_notifications, emit_notification_event

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
    )


@override_settings(EMAIL_NOTIFICATIONS_ENABLED=False, DEFAULT_FROM_EMAIL="")
def test_notification_delivery_skips_safely_when_email_is_not_configured():
    bidder = create_user("bidder")
    notification = emit_notification_event(
        event_type="winner_assigned",
        recipient=bidder,
        entity_type="lot",
        entity_id="10",
        metadata={
            "lot_id": 10,
            "auction_id": 1,
            "winning_bid_id": 5,
            "amount": str(Decimal("130.00")),
        },
    )

    result = deliver_pending_notifications()

    notification.refresh_from_db()
    assert result == {"seen": 1, "sent": 0, "skipped": 1, "failed": 0}
    assert notification.status == NotificationStatus.SKIPPED
    assert "disabled" in notification.error_message
    assert AuditLog.objects.filter(
        action=AuditAction.NOTIFICATION_EVENT,
        metadata__notification_id=notification.id,
        metadata__delivery_status=NotificationStatus.SKIPPED,
    ).exists()


@override_settings(
    EMAIL_NOTIFICATIONS_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notifications@bidals.test",
)
def test_notification_delivery_sends_with_configured_email_backend():
    bidder = create_user("bidder")
    notification = OutboundNotification.objects.create(
        recipient=bidder,
        recipient_email=bidder.email,
        notification_type="winner_assigned",
        subject="Winner",
        body="You won.",
        related_entity_type="lot",
        related_entity_id="10",
    )

    result = deliver_pending_notifications()

    notification.refresh_from_db()
    assert result == {"seen": 1, "sent": 1, "skipped": 0, "failed": 0}
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [bidder.email]


def test_user_can_mark_own_notification_read_and_not_others():
    bidder = create_user("bidder")
    other_bidder = create_user("other_bidder")
    notification = emit_notification_event(
        event_type="seller_contacted",
        recipient=bidder,
        entity_type="fulfillment",
        entity_id="1",
        metadata={"fulfillment_id": 1, "lot_id": 1, "auction_id": 1},
    )
    other_notification = emit_notification_event(
        event_type="seller_contacted",
        recipient=other_bidder,
        entity_type="fulfillment",
        entity_id="2",
        metadata={"fulfillment_id": 2, "lot_id": 2, "auction_id": 1},
    )
    client = APIClient()
    client.force_authenticate(user=bidder)

    list_response = client.get("/api/account/notifications/")
    count_response = client.get("/api/account/notifications/unread-count/")
    read_response = client.patch(f"/api/account/notifications/{notification.id}/read/")
    count_after_read_response = client.get("/api/account/notifications/unread-count/")
    other_read_response = client.patch(f"/api/account/notifications/{other_notification.id}/read/")

    notification.refresh_from_db()
    other_notification.refresh_from_db()
    assert list_response.status_code == 200
    assert list_response.data["unread_count"] == 1
    assert count_response.status_code == 200
    assert count_response.data["unread_count"] == 1
    assert read_response.status_code == 200
    assert read_response.data["is_read"] is True
    assert count_after_read_response.data["unread_count"] == 0
    assert notification.read_at is not None
    assert other_read_response.status_code == 404
    assert other_notification.read_at is None
    assert AuditLog.objects.filter(action=AuditAction.NOTIFICATION_MARKED_READ, metadata__notification_id=notification.id).exists()


def test_mark_all_read_only_affects_current_user():
    bidder = create_user("bidder")
    other_bidder = create_user("other_bidder")
    notification = emit_notification_event(
        event_type="seller_contacted",
        recipient=bidder,
        entity_type="fulfillment",
        entity_id="1",
        metadata={"fulfillment_id": 1},
    )
    other_notification = emit_notification_event(
        event_type="seller_contacted",
        recipient=other_bidder,
        entity_type="fulfillment",
        entity_id="2",
        metadata={"fulfillment_id": 2},
    )
    client = APIClient()
    client.force_authenticate(user=bidder)

    response = client.post("/api/account/notifications/mark-all-read/")

    notification.refresh_from_db()
    other_notification.refresh_from_db()
    assert response.status_code == 200
    assert response.data["marked_read"] == 1
    assert notification.read_at is not None
    assert other_notification.read_at is None
    assert AuditLog.objects.filter(action=AuditAction.NOTIFICATIONS_MARKED_READ, metadata__count=1).exists()
