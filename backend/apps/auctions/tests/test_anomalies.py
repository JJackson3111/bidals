from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidRejectionReason,
    BidStatus,
    Lot,
    LotStatus,
)
from apps.auctions.services.anomalies import detect_bid_anomalies

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_lot(seller):
    now = timezone.now()
    auction = Auction.objects.create(
        title="Anomaly Auction",
        description="Auction for anomaly tests.",
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(minutes=10),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )
    return Lot.objects.create(
        auction=auction,
        title="Anomaly Lot",
        description="Lot for anomaly tests.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.OPEN,
    )


@override_settings(BID_ANOMALY_REJECT_THRESHOLD=2, BID_ANOMALY_RATE_LIMIT_THRESHOLD=2, ALERT_WEBHOOK_URL="")
def test_rejected_bid_anomaly_creates_audit_and_graceful_alert_event():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    lot = create_lot(seller)
    now = timezone.now()

    for amount in ("101.00", "102.00"):
        Bid.objects.create(
            lot=lot,
            bidder=bidder,
            amount=Decimal(amount),
            status=BidStatus.REJECTED,
            rejection_reason=BidRejectionReason.INVALID_INCREMENT,
            server_timestamp=now,
        )

    anomalies = detect_bid_anomalies(window_minutes=60, now=now)
    duplicate_anomalies = detect_bid_anomalies(window_minutes=60, now=now)

    assert len(anomalies) == 1
    assert duplicate_anomalies == []
    assert anomalies[0].anomaly_type == "repeated_rejected_bids"
    assert AuditLog.objects.filter(
        action=AuditAction.BID_ANOMALY_DETECTED,
        metadata__anomaly_key=f"rejected:{bidder.id}:{BidRejectionReason.INVALID_INCREMENT}",
    ).count() == 1
    alert = AuditLog.objects.get(action=AuditAction.ALERT_TRIGGERED)
    assert alert.metadata["event_type"] == "bid_anomaly_detected"
    assert alert.metadata["delivery_status"] == "not_configured"


@override_settings(BID_ANOMALY_REJECT_THRESHOLD=5, BID_ANOMALY_RATE_LIMIT_THRESHOLD=2, ALERT_WEBHOOK_URL="")
def test_rate_limit_anomaly_uses_bid_rejection_audit_logs():
    bidder = create_user("bidder")
    now = timezone.now()
    for _ in range(2):
        AuditLog.objects.create(
            actor=bidder,
            action=AuditAction.BID_REJECTED,
            entity_type="lot",
            entity_id="1",
            server_timestamp=now,
            metadata={
                "bidder_id": bidder.id,
                "reason": BidRejectionReason.RATE_LIMITED,
            },
        )

    anomalies = detect_bid_anomalies(window_minutes=60, now=now)

    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == "repeated_rate_limits"
    assert AuditLog.objects.filter(
        action=AuditAction.BID_ANOMALY_DETECTED,
        metadata__anomaly_key=f"rate_limited:{bidder.id}",
    ).exists()
