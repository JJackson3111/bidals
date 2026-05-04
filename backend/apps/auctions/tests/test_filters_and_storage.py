from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, BidStatus, Lot, LotStatus
from bidals.storage import validate_s3_settings

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_auction(*, seller, title, status, offset_days=0):
    now = timezone.now() + timedelta(days=offset_days)
    return Auction.objects.create(
        title=title,
        description=f"{title} description",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(hours=2),
        status=status,
        created_by=seller,
    )


def create_lot(*, auction, title, status):
    return Lot.objects.create(
        auction=auction,
        title=title,
        description=f"{title} description",
        starting_price=Decimal("20.00"),
        current_price=Decimal("20.00"),
        bid_increment=Decimal("5.00"),
        status=status,
    )


def test_seller_management_filters_remain_scoped_to_their_own_private_data():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    own_draft = create_auction(seller=seller, title="Private Seller Draft", status=AuctionStatus.DRAFT)
    other_draft = create_auction(seller=other_seller, title="Private Other Draft", status=AuctionStatus.DRAFT)
    public_live = create_auction(seller=other_seller, title="Public Live Sale", status=AuctionStatus.LIVE)
    create_lot(auction=own_draft, title="Own Draft Lot", status=LotStatus.DRAFT)
    create_lot(auction=other_draft, title="Other Draft Lot", status=LotStatus.DRAFT)
    create_lot(auction=public_live, title="Public Open Lot", status=LotStatus.OPEN)

    client = APIClient()
    client.force_authenticate(user=seller)

    auction_response = client.get("/api/auctions/", {"status": "draft", "search": "Private"})
    lot_response = client.get("/api/lots/", {"status": "draft", "search": "Draft"})

    assert auction_response.status_code == 200
    assert [auction["title"] for auction in auction_response.data["results"]] == ["Private Seller Draft"]
    assert lot_response.status_code == 200
    assert [lot["title"] for lot in lot_response.data["results"]] == ["Own Draft Lot"]


def test_admin_audit_filters_by_actor_bid_status_and_metadata():
    admin = create_user("admin", role=UserRole.ADMIN)
    actor = create_user("bidder")
    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.BID_ACCEPTED,
        entity_type="bid",
        entity_id="100",
        metadata={"lot_id": 5, "note": "needle"},
    )
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.BID_REJECTED,
        entity_type="bid",
        entity_id="101",
        metadata={"lot_id": 6, "note": "other"},
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/audit/",
        {
            "actor": "bidder",
            "bid_status": "accepted",
            "entity_type": "bid",
            "metadata_search": "needle",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["action"] == AuditAction.BID_ACCEPTED


def test_validate_s3_settings_requires_cloudflare_r2_values():
    with pytest.raises(ImproperlyConfigured, match="USE_S3=True requires"):
        validate_s3_settings(
            {
                "AWS_ACCESS_KEY_ID": "key",
                "AWS_SECRET_ACCESS_KEY": "",
                "AWS_STORAGE_BUCKET_NAME": "bucket",
                "AWS_S3_ENDPOINT_URL": "",
                "AWS_S3_REGION_NAME": "auto",
            }
        )


def test_validate_s3_settings_accepts_required_cloudflare_r2_values():
    validate_s3_settings(
        {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_STORAGE_BUCKET_NAME": "bucket",
            "AWS_S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
            "AWS_S3_REGION_NAME": "auto",
        }
    )
