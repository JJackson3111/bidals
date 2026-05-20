from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Lot, LotStatus

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_auction(*, seller, title="Estate Sale", status=AuctionStatus.LIVE):
    now = timezone.now()
    return Auction.objects.create(
        title=title,
        description=f"{title} description",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        status=status,
        created_by=seller,
    )


def create_lot(*, auction, title="Collector Lot", status=LotStatus.OPEN):
    return Lot.objects.create(
        auction=auction,
        title=title,
        description=f"{title} description",
        starting_price=Decimal("20.00"),
        current_price=Decimal("20.00"),
        bid_increment=Decimal("5.00"),
        status=status,
    )


def test_seller_can_access_their_own_auction_management_detail():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.get(f"/api/auctions/{auction.id}/manage/")

    assert response.status_code == 200
    assert response.data["id"] == auction.id
    assert response.data["created_by"] == seller.id


def test_seller_can_access_their_own_ended_auction_management_detail():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller, status=AuctionStatus.ENDED)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.get(f"/api/auctions/{auction.id}/manage/")

    assert response.status_code == 200
    assert response.data["id"] == auction.id
    assert response.data["created_by"] == seller.id
    assert response.data["status"] == AuctionStatus.ENDED


def test_unrelated_seller_cannot_access_other_seller_auction_management_detail():
    owner = create_user("owner", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    auction = create_auction(seller=owner)
    client = APIClient()
    client.force_authenticate(user=other_seller)

    response = client.get(f"/api/auctions/{auction.id}/manage/")

    assert response.status_code in {403, 404}


def test_unrelated_seller_cannot_update_other_seller_auction():
    owner = create_user("owner", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    auction = create_auction(seller=owner)
    client = APIClient()
    client.force_authenticate(user=other_seller)

    response = client.patch(
        f"/api/auctions/{auction.id}/",
        {"title": "Unauthorized rename"},
        format="json",
    )

    assert response.status_code in {403, 404}
    auction.refresh_from_db()
    assert auction.title == "Estate Sale"


def test_seller_can_extend_live_auction_end_time_and_edit_is_audited():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    new_end_time = auction.end_time + timedelta(minutes=30)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/auctions/{auction.id}/",
        {"end_time": new_end_time.isoformat()},
        format="json",
    )

    auction.refresh_from_db()
    assert response.status_code == 200
    assert auction.end_time == new_end_time
    assert AuditLog.objects.filter(
        action=AuditAction.SELLER_LIVE_TIMING_UPDATED,
        metadata__auction_id=auction.id,
        metadata__reason="seller_live_timing_edit",
    ).exists()


def test_seller_cannot_shorten_live_auction_end_time():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    shortened_end_time = auction.end_time - timedelta(minutes=30)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/auctions/{auction.id}/",
        {"end_time": shortened_end_time.isoformat()},
        format="json",
    )

    auction.refresh_from_db()
    assert response.status_code == 400
    assert auction.end_time != shortened_end_time
    assert "end time can only be extended" in str(response.data["end_time"][0])


def test_seller_cannot_move_live_auction_end_time_into_past():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    past_end_time = timezone.now() - timedelta(minutes=1)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/auctions/{auction.id}/",
        {"end_time": past_end_time.isoformat()},
        format="json",
    )

    auction.refresh_from_db()
    assert response.status_code == 400
    assert auction.end_time != past_end_time
    assert "end time must stay in the future" in str(response.data["end_time"][0])


def test_admin_can_access_any_auction_management_detail():
    owner = create_user("owner", role=UserRole.SELLER)
    admin = create_user("admin", role=UserRole.ADMIN)
    auction = create_auction(seller=owner)
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(f"/api/auctions/{auction.id}/manage/")

    assert response.status_code == 200
    assert response.data["id"] == auction.id


def test_public_auction_detail_remains_publicly_viewable():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    client = APIClient()

    response = client.get(f"/api/auctions/{auction.id}/")

    assert response.status_code == 200
    assert response.data["id"] == auction.id
    assert response.data["effective_status"] == AuctionStatus.LIVE
    assert response.data["server_now"] is not None
    assert response.data["bidding_opens_at"] is not None
    assert response.data["bidding_closes_at"] is not None
    assert response.data["can_bid"] is True


def test_seller_browse_lists_only_include_their_own_auctions_and_lots():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    own_auction = create_auction(seller=seller, title="Own Live Sale")
    other_auction = create_auction(seller=other_seller, title="Other Live Sale")
    own_lot = create_lot(auction=own_auction, title="Own Open Lot")
    create_lot(auction=other_auction, title="Other Open Lot")
    client = APIClient()
    client.force_authenticate(user=seller)

    auction_response = client.get("/api/auctions/")
    lot_response = client.get("/api/lots/")

    assert auction_response.status_code == 200
    assert [auction["id"] for auction in auction_response.data["results"]] == [own_auction.id]
    assert lot_response.status_code == 200
    assert [lot["id"] for lot in lot_response.data["results"]] == [own_lot.id]


def test_seller_cannot_access_other_seller_public_auction_or_lot_detail():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    other_auction = create_auction(seller=other_seller, title="Other Live Sale")
    other_lot = create_lot(auction=other_auction, title="Other Open Lot")
    client = APIClient()
    client.force_authenticate(user=seller)

    auction_response = client.get(f"/api/auctions/{other_auction.id}/")
    lot_response = client.get(f"/api/lots/{other_lot.id}/")

    assert auction_response.status_code == 404
    assert lot_response.status_code == 404


def test_public_and_bidder_browsing_still_see_public_auctions_and_lots():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder", role=UserRole.BIDDER)
    public_auction = create_auction(seller=seller, title="Public Live Sale")
    private_auction = create_auction(seller=seller, title="Private Draft Sale", status=AuctionStatus.DRAFT)
    public_lot = create_lot(auction=public_auction, title="Public Open Lot")
    create_lot(auction=private_auction, title="Private Draft Lot", status=LotStatus.DRAFT)

    anonymous_client = APIClient()
    bidder_client = APIClient()
    bidder_client.force_authenticate(user=bidder)

    anonymous_auction_response = anonymous_client.get("/api/auctions/")
    anonymous_lot_response = anonymous_client.get("/api/lots/")
    bidder_auction_response = bidder_client.get("/api/auctions/")
    bidder_lot_response = bidder_client.get("/api/lots/")
    bidder_detail_response = bidder_client.get(f"/api/auctions/{public_auction.id}/")

    assert anonymous_auction_response.status_code == 200
    assert [auction["id"] for auction in anonymous_auction_response.data["results"]] == [public_auction.id]
    assert anonymous_lot_response.status_code == 200
    assert [lot["id"] for lot in anonymous_lot_response.data["results"]] == [public_lot.id]
    assert bidder_auction_response.status_code == 200
    assert [auction["id"] for auction in bidder_auction_response.data["results"]] == [public_auction.id]
    assert bidder_lot_response.status_code == 200
    assert [lot["id"] for lot in bidder_lot_response.data["results"]] == [public_lot.id]
    assert bidder_lot_response.data["results"][0]["effective_status"] == LotStatus.OPEN
    assert bidder_lot_response.data["results"][0]["can_bid"] is True
    assert bidder_lot_response.data["results"][0]["server_now"] is not None
    assert bidder_detail_response.status_code == 200


def test_admin_browsing_can_see_all_auctions_and_lots():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    admin = create_user("admin", role=UserRole.ADMIN)
    own_auction = create_auction(seller=seller, title="Seller Live Sale")
    other_auction = create_auction(seller=other_seller, title="Other Draft Sale", status=AuctionStatus.DRAFT)
    own_lot = create_lot(auction=own_auction, title="Seller Open Lot")
    other_lot = create_lot(auction=other_auction, title="Other Draft Lot", status=LotStatus.DRAFT)
    client = APIClient()
    client.force_authenticate(user=admin)

    auction_response = client.get("/api/auctions/", {"sort": "oldest"})
    lot_response = client.get("/api/lots/", {"sort": "oldest"})
    auction_detail_response = client.get(f"/api/auctions/{other_auction.id}/")
    lot_detail_response = client.get(f"/api/lots/{other_lot.id}/")

    assert auction_response.status_code == 200
    assert {auction["id"] for auction in auction_response.data["results"]} == {own_auction.id, other_auction.id}
    assert lot_response.status_code == 200
    assert {lot["id"] for lot in lot_response.data["results"]} == {own_lot.id, other_lot.id}
    assert auction_detail_response.status_code == 200
    assert lot_detail_response.status_code == 200
