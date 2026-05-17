from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.auctions.models import Auction, AuctionStatus

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


def test_seller_can_access_their_own_auction_management_detail():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.get(f"/api/auctions/{auction.id}/manage/")

    assert response.status_code == 200
    assert response.data["id"] == auction.id
    assert response.data["created_by"] == seller.id


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

    assert response.status_code == 403
    auction.refresh_from_db()
    assert auction.title == "Estate Sale"


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
