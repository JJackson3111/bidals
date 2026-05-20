from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.auctions.models import Auction, AuctionStatus, BidRejectionReason, Lot, LotStatus
from apps.auctions.services.bidding import place_bid

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_auction(*, seller, status, starts_at=None, ends_at=None):
    now = timezone.now()
    start_time = starts_at or now - timedelta(minutes=5)
    return Auction.objects.create(
        title=f"{status} auction",
        description="Status rule test auction.",
        start_time=start_time,
        end_time=ends_at or start_time + timedelta(hours=1),
        status=status,
        created_by=seller,
    )


def lot_payload(auction, *, status=LotStatus.OPEN):
    return {
        "auction": auction.id,
        "title": "Status Rule Lot",
        "description": "Status rule lot.",
        "starting_price": "10.00",
        "reserve_price": None,
        "bid_increment": "5.00",
        "status": status,
        "images": [],
    }


@pytest.mark.parametrize("auction_status", [AuctionStatus.DRAFT, AuctionStatus.ENDED, AuctionStatus.CANCELLED])
def test_lot_cannot_be_created_open_for_non_bid_eligible_auction_statuses(auction_status):
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller, status=auction_status)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.post("/api/lots/", lot_payload(auction), format="json")

    assert response.status_code == 400
    assert "Lots can only be marked open" in str(response.data["status"][0])
    assert not Lot.objects.filter(auction=auction).exists()


def test_scheduled_auction_can_prepare_open_lot_but_bidding_is_not_live():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder", role=UserRole.BIDDER)
    now = timezone.now()
    auction = create_auction(
        seller=seller,
        status=AuctionStatus.SCHEDULED,
        starts_at=now + timedelta(minutes=5),
        ends_at=now + timedelta(hours=1),
    )
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.post("/api/lots/", lot_payload(auction), format="json")

    assert response.status_code == 201
    lot = Lot.objects.get(pk=response.data["id"])
    result = place_bid(bidder, lot.id, Decimal("15.00"))
    assert result.reason == BidRejectionReason.AUCTION_NOT_STARTED
    lot.refresh_from_db()
    assert lot.current_price == Decimal("10.00")


def test_lot_cannot_be_updated_open_when_moved_to_draft_auction():
    seller = create_user("seller", role=UserRole.SELLER)
    live_auction = create_auction(seller=seller, status=AuctionStatus.LIVE)
    draft_auction = create_auction(seller=seller, status=AuctionStatus.DRAFT)
    lot = Lot.objects.create(
        auction=live_auction,
        title="Move Me",
        description="Move test.",
        starting_price=Decimal("10.00"),
        current_price=Decimal("10.00"),
        bid_increment=Decimal("5.00"),
        status=LotStatus.OPEN,
    )
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/lots/{lot.id}/",
        {"auction": draft_auction.id, "status": LotStatus.OPEN},
        format="json",
    )

    assert response.status_code == 400
    assert "Lots can only be marked open" in str(response.data["status"][0])
