from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Lot, LotImage, LotStatus

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_lot():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    auction = Auction.objects.create(
        title="Image Auction",
        description="A public auction.",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(minutes=5),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title="Image Lot",
        description="A test lot.",
        starting_price=Decimal("90.00"),
        current_price=Decimal("90.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.OPEN,
    )
    return seller, lot


def upload_file(name="lot.png"):
    return SimpleUploadedFile(name, b"image-bytes", content_type="image/png")


@override_settings(MEDIA_ROOT="/tmp/bidals-test-media")
def test_auction_owner_can_upload_lot_image():
    seller, lot = create_lot()
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file(), "alt_text": "Front view", "sort_order": 1},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["alt_text"] == "Front view"
    assert response.data["sort_order"] == 1
    assert response.data["image_url"]
    assert LotImage.objects.filter(lot=lot, alt_text="Front view").exists()
    assert AuditLog.objects.filter(
        action=AuditAction.LOT_UPDATED,
        metadata__lot_id=lot.id,
        metadata__updated_fields=["uploaded_images"],
    ).exists()


def test_bidder_cannot_upload_lot_image():
    _, lot = create_lot()
    bidder = create_user("bidder", role=UserRole.BIDDER)
    client = APIClient()
    client.force_authenticate(user=bidder)

    response = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file(), "alt_text": "Blocked"},
        format="multipart",
    )

    assert response.status_code == 403
    assert not LotImage.objects.filter(lot=lot).exists()


@override_settings(MEDIA_ROOT="/tmp/bidals-test-media")
def test_public_lot_detail_includes_uploaded_image_urls():
    seller, lot = create_lot()
    client = APIClient()
    client.force_authenticate(user=seller)
    client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file(), "alt_text": "Public image"},
        format="multipart",
    )
    client.force_authenticate(user=None)

    response = client.get(f"/api/lots/{lot.id}/")

    assert response.status_code == 200
    assert len(response.data["uploaded_images"]) == 1
    assert response.data["uploaded_images"][0]["alt_text"] == "Public image"
    assert response.data["uploaded_images"][0]["image_url"]


@override_settings(MEDIA_ROOT="/tmp/bidals-test-media")
def test_auction_owner_can_delete_lot_image():
    seller, lot = create_lot()
    client = APIClient()
    client.force_authenticate(user=seller)
    upload = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file(), "alt_text": "Delete me"},
        format="multipart",
    )
    image_id = upload.data["id"]

    response = client.delete(f"/api/lots/{lot.id}/images/{image_id}/")

    assert response.status_code == 204
    assert not LotImage.objects.filter(pk=image_id).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.LOT_UPDATED,
        metadata__lot_id=lot.id,
        metadata__image_deleted__image_id=image_id,
    ).exists()


@override_settings(MEDIA_ROOT="/tmp/bidals-test-media")
def test_seller_cannot_delete_another_sellers_lot_image():
    seller, lot = create_lot()
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    client = APIClient()
    client.force_authenticate(user=seller)
    upload = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file(), "alt_text": "Protected"},
        format="multipart",
    )
    image_id = upload.data["id"]

    client.force_authenticate(user=other_seller)
    response = client.delete(f"/api/lots/{lot.id}/images/{image_id}/")

    assert response.status_code == 403
    assert LotImage.objects.filter(pk=image_id).exists()


@override_settings(MEDIA_ROOT="/tmp/bidals-test-media")
def test_auction_owner_can_reorder_lot_images():
    seller, lot = create_lot()
    client = APIClient()
    client.force_authenticate(user=seller)
    first = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file("first.png"), "alt_text": "First", "sort_order": 1},
        format="multipart",
    )
    second = client.post(
        f"/api/lots/{lot.id}/images/",
        {"image": upload_file("second.png"), "alt_text": "Second", "sort_order": 2},
        format="multipart",
    )

    response = client.patch(
        f"/api/lots/{lot.id}/images/reorder/",
        {
            "image_order": [
                {"id": second.data["id"], "sort_order": 1},
                {"id": first.data["id"], "sort_order": 2},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert [image["id"] for image in response.data] == [second.data["id"], first.data["id"]]
    assert LotImage.objects.get(pk=second.data["id"]).sort_order == 1
    assert LotImage.objects.get(pk=first.data["id"]).sort_order == 2
    assert AuditLog.objects.filter(
        action=AuditAction.LOT_UPDATED,
        metadata__lot_id=lot.id,
        metadata__image_reorder__0__id=second.data["id"],
    ).exists()
