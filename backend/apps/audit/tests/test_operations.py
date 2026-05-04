from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Bid, BidRejectionReason, BidStatus, Lot, LotStatus

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
        title="Ops Auction",
        description="Operational test auction.",
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(hours=1),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )
    return Lot.objects.create(
        auction=auction,
        title="Ops Lot",
        description="Operational test lot.",
        starting_price=Decimal("50.00"),
        current_price=Decimal("50.00"),
        bid_increment=Decimal("5.00"),
        status=LotStatus.OPEN,
    )


@override_settings(BID_ANOMALY_REJECT_THRESHOLD=3)
def test_operations_summary_is_admin_only_and_reports_bid_signals():
    admin = create_user("admin", role=UserRole.ADMIN)
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    lot = create_lot(seller)
    now = timezone.now()

    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("55.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=now,
    )
    for amount in ("56.00", "57.00", "58.00"):
        Bid.objects.create(
            lot=lot,
            bidder=bidder,
            amount=Decimal(amount),
            status=BidStatus.REJECTED,
            rejection_reason=BidRejectionReason.INVALID_INCREMENT,
            server_timestamp=now,
        )

    AuditLog.objects.create(
        actor=bidder,
        action=AuditAction.BID_REJECTED,
        entity_type="bid",
        entity_id="server-error",
        metadata={"reason": BidRejectionReason.SERVER_ERROR, "lot_id": lot.id},
        server_timestamp=now,
    )

    client = APIClient()
    seller_response = client.get("/api/operations/")
    assert seller_response.status_code in {401, 403}

    client.force_authenticate(user=seller)
    seller_response = client.get("/api/operations/")
    assert seller_response.status_code == 403

    client.force_authenticate(user=admin)
    admin_response = client.get("/api/operations/", {"window_minutes": "120"})

    assert admin_response.status_code == 200
    assert admin_response.data["window_minutes"] == 120
    assert admin_response.data["summary"]["total_bids"] == 4
    assert admin_response.data["summary"]["accepted_bids"] == 1
    assert admin_response.data["summary"]["rejected_bids"] == 3
    assert admin_response.data["summary"]["recent_server_bid_errors"] == 1
    assert admin_response.data["summary"]["suspicious_repeated_failures"] == 1
    assert admin_response.data["thresholds"]["bid_anomaly_reject_threshold"] == 3
    assert admin_response.data["recent_accepted_bids"][0]["lot_title"] == "Ops Lot"
    assert admin_response.data["rejected_by_reason"][0]["rejection_reason"] == BidRejectionReason.INVALID_INCREMENT


def test_health_response_includes_request_id_header():
    client = APIClient()
    response = client.get("/api/health/", HTTP_X_REQUEST_ID="phase8-test-request")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "phase8-test-request"
