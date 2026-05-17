from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, Lot, LotStatus, LotWinnerStatus

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_finalized_lot(*, seller, title, winner=None, winner_status=LotWinnerStatus.WINNER_ASSIGNED):
    now = timezone.now()
    auction = Auction.objects.create(
        title=f"{title} Auction",
        description="Finalized auction.",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        status=AuctionStatus.ENDED,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title=title,
        description="Finalized lot.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("130.00"),
        reserve_price=Decimal("120.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.SOLD if winner else LotStatus.CLOSED,
        winner_status=winner_status,
        winner_calculated_at=now,
        winner=winner,
    )
    if winner:
        bid = Bid.objects.create(
            lot=lot,
            bidder=winner,
            amount=Decimal("130.00"),
            status=BidStatus.ACCEPTED,
            server_timestamp=now - timedelta(minutes=5),
        )
        lot.winning_bid = bid
        lot.save(update_fields=("winning_bid",))
    return auction, lot


def test_seller_can_review_only_their_own_winners():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    own_auction, own_lot = create_finalized_lot(seller=seller, title="Own Lot", winner=bidder)
    other_auction, _ = create_finalized_lot(seller=other_seller, title="Other Lot", winner=bidder)

    client = APIClient()
    client.force_authenticate(user=seller)

    list_response = client.get("/api/dashboard/winners/")
    own_response = client.get(f"/api/auctions/{own_auction.id}/results/")
    other_response = client.get(f"/api/auctions/{other_auction.id}/results/")

    assert list_response.status_code == 200
    assert [item["lot_id"] for item in list_response.data["results"]] == [own_lot.id]
    assert list_response.data["summary"]["winner_assigned"] == 1
    assert own_response.status_code == 200
    assert own_response.data["results"][0]["winner_username"] == bidder.username
    assert other_response.status_code in {403, 404}


def test_admin_can_review_all_winners():
    admin = create_user("admin", role=UserRole.ADMIN)
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    create_finalized_lot(seller=seller, title="Own Lot", winner=bidder)
    create_finalized_lot(
        seller=other_seller,
        title="Reserve Lot",
        winner=None,
        winner_status=LotWinnerStatus.RESERVE_NOT_MET,
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/dashboard/winners/")

    assert response.status_code == 200
    assert response.data["summary"]["total_lots"] == 2
    assert response.data["summary"]["winner_assigned"] == 1
    assert response.data["summary"]["reserve_not_met"] == 1


def test_bidder_cannot_access_winner_management_api():
    bidder = create_user("bidder")
    client = APIClient()
    client.force_authenticate(user=bidder)

    response = client.get("/api/dashboard/winners/")

    assert response.status_code == 403
