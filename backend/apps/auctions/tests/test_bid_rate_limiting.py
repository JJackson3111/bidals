from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

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

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_bid_rate_cache():
    cache.clear()
    yield
    cache.clear()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_live_lot():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    auction = Auction.objects.create(
        title="Rate Limited Auction",
        description="A live auction.",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(minutes=5),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title="Rate Limited Lot",
        description="A test lot.",
        starting_price=Decimal("90.00"),
        current_price=Decimal("90.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.OPEN,
    )
    return lot


@override_settings(BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS=1, BID_RATE_LIMIT_WINDOW_SECONDS=60)
def test_authenticated_bidder_is_rate_limited_after_allowed_attempt():
    lot = create_live_lot()
    bidder = create_user("bidder")
    client = APIClient()
    client.force_authenticate(user=bidder)

    first = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "100.00"}, format="json")
    second = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "110.00"}, format="json")

    lot.refresh_from_db()

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.data["status"] == "rejected"
    assert second.data["reason"] == BidRejectionReason.RATE_LIMITED
    assert second.data["current_price"] == "100.00"
    assert "retry_after" in second.data
    assert lot.current_price == Decimal("100.00")
    assert not Bid.objects.filter(lot=lot, amount=Decimal("110.00")).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED,
        metadata__reason=BidRejectionReason.RATE_LIMITED,
        metadata__bidder_id=bidder.id,
    ).exists()


@override_settings(BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS=1, BID_RATE_LIMIT_WINDOW_SECONDS=60)
def test_anonymous_bid_attempts_are_rate_limited_after_first_rejection():
    lot = create_live_lot()
    client = APIClient()

    first = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "100.00"}, format="json")
    second = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "100.00"}, format="json")

    lot.refresh_from_db()

    assert first.status_code == 401
    assert first.data["reason"] == BidRejectionReason.UNAUTHENTICATED
    assert second.status_code == 429
    assert second.data["reason"] == BidRejectionReason.RATE_LIMITED
    assert second.data["current_price"] == "90.00"
    assert lot.current_price == Decimal("90.00")
    assert AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED,
        metadata__reason=BidRejectionReason.RATE_LIMITED,
        metadata__bidder_id=None,
    ).exists()


def test_valid_bid_succeeds_when_rate_limit_cache_is_unavailable():
    lot = create_live_lot()
    bidder = create_user("cache_outage_bidder")
    client = APIClient()
    client.force_authenticate(user=bidder)

    with patch("apps.auctions.services.rate_limits.cache.add", side_effect=ConnectionError("redis unavailable")):
        response = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "100.00"}, format="json")

    lot.refresh_from_db()
    bid = Bid.objects.get(lot=lot, bidder=bidder)
    assert response.status_code == 201
    assert response.data["status"] == BidStatus.ACCEPTED
    assert response.data["current_price"] == "100.00"
    assert bid.status == BidStatus.ACCEPTED
    assert lot.current_price == Decimal("100.00")
    assert AuditLog.objects.filter(action=AuditAction.BID_ACCEPTED, entity_id=str(bid.id)).exists()


def test_invalid_bid_returns_rejection_when_rate_limit_cache_is_unavailable():
    lot = create_live_lot()
    bidder = create_user("cache_outage_invalid_bidder")
    client = APIClient()
    client.force_authenticate(user=bidder)

    with patch("apps.auctions.services.rate_limits.cache.add", side_effect=ConnectionError("redis unavailable")):
        response = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "95.00"}, format="json")

    lot.refresh_from_db()
    bid = Bid.objects.get(lot=lot, bidder=bidder)
    assert response.status_code == 409
    assert response.data["status"] == BidStatus.REJECTED
    assert response.data["reason"] == BidRejectionReason.INVALID_INCREMENT
    assert response.data["current_price"] == "90.00"
    assert bid.status == BidStatus.REJECTED
    assert bid.rejection_reason == BidRejectionReason.INVALID_INCREMENT
    assert lot.current_price == Decimal("90.00")
    assert AuditLog.objects.filter(action=AuditAction.BID_REJECTED, entity_id=str(bid.id)).exists()


def test_anonymous_bid_returns_controlled_rejection_when_rate_limit_cache_is_unavailable():
    lot = create_live_lot()
    client = APIClient()

    with patch("apps.auctions.services.rate_limits.cache.add", side_effect=ConnectionError("redis unavailable")):
        response = client.post(f"/api/lots/{lot.id}/bid/", {"amount": "100.00"}, format="json")

    lot.refresh_from_db()
    assert response.status_code == 401
    assert response.data["status"] == BidStatus.REJECTED
    assert response.data["reason"] == BidRejectionReason.UNAUTHENTICATED
    assert lot.current_price == Decimal("90.00")
    assert not Bid.objects.filter(lot=lot).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED,
        metadata__reason=BidRejectionReason.UNAUTHENTICATED,
    ).exists()
