from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidStatus,
    FulfillmentRecord,
    FulfillmentStatus,
    Lot,
    LotStatus,
    LotWinnerStatus,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_fulfillment(*, seller, winner, title="Won Lot"):
    now = timezone.now()
    auction = Auction.objects.create(
        title=f"{title} Auction",
        description="Fulfillment test auction.",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        status=AuctionStatus.ENDED,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title=title,
        description="Fulfillment test lot.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("130.00"),
        reserve_price=Decimal("120.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.SOLD,
        winner=winner,
        winner_status=LotWinnerStatus.WINNER_ASSIGNED,
        winner_calculated_at=now,
    )
    bid = Bid.objects.create(
        lot=lot,
        bidder=winner,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=now - timedelta(minutes=5),
    )
    lot.winning_bid = bid
    lot.save(update_fields=("winning_bid",))
    return FulfillmentRecord.objects.create(
        lot=lot,
        auction=auction,
        winning_bid=bid,
        winner=winner,
    )


def test_seller_can_view_and_update_own_fulfillment_record_with_audit_log():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    record = create_fulfillment(seller=seller, winner=winner)
    client = APIClient()
    client.force_authenticate(user=seller)

    list_response = client.get("/api/dashboard/fulfillment/")
    patch_response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {
            "status": FulfillmentStatus.SELLER_CONTACTED,
            "confirmation_notes": "Winner replied by email.",
            "seller_notes": "Arrange pickup on Friday.",
            "public_winner_message": "Seller has contacted you.",
        },
        format="json",
    )

    record.refresh_from_db()

    assert list_response.status_code == 200
    assert list_response.data["summary"]["total"] == 1
    assert patch_response.status_code == 200
    assert patch_response.data["status"] == FulfillmentStatus.SELLER_CONTACTED
    assert patch_response.data["allowed_next_statuses"] == [
        FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY,
        FulfillmentStatus.COMPLETED,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.DISPUTED,
    ]
    assert record.status == FulfillmentStatus.SELLER_CONTACTED
    assert record.last_follow_up_at is not None
    assert AuditLog.objects.filter(
        action=AuditAction.FULFILLMENT_STATUS_CHANGED,
        metadata__fulfillment_id=record.id,
        metadata__old_status=FulfillmentStatus.PENDING_CONFIRMATION,
        metadata__new_status=FulfillmentStatus.SELLER_CONTACTED,
    ).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.FULFILLMENT_CONFIRMATION_NOTES_UPDATED,
        metadata__fulfillment_id=record.id,
    ).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED,
        metadata__fulfillment_id=record.id,
    ).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.NOTIFICATION_EVENT,
        metadata__event_type="seller_contacted",
        metadata__fulfillment_id=record.id,
    ).exists()


def test_seller_cannot_view_or_update_other_seller_fulfillment():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    winner = create_user("winner")
    record = create_fulfillment(seller=other_seller, winner=winner)
    client = APIClient()
    client.force_authenticate(user=seller)

    list_response = client.get("/api/dashboard/fulfillment/")
    patch_response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.COMPLETED},
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.data["summary"]["total"] == 0
    assert patch_response.status_code == 404


def test_admin_can_view_and_update_all_fulfillment_records():
    admin = create_user("admin", role=UserRole.ADMIN)
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    record = create_fulfillment(seller=seller, winner=winner)
    record.status = FulfillmentStatus.SELLER_CONTACTED
    record.save(update_fields=("status", "updated_at"))
    client = APIClient()
    client.force_authenticate(user=admin)

    patch_response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.COMPLETED, "admin_notes": "Manually verified."},
        format="json",
    )

    record.refresh_from_db()
    assert patch_response.status_code == 200
    assert record.status == FulfillmentStatus.COMPLETED
    assert record.completed_at is not None
    assert AuditLog.objects.filter(action=AuditAction.FULFILLMENT_COMPLETED, metadata__fulfillment_id=record.id).exists()
    assert AuditLog.objects.filter(action=AuditAction.FULFILLMENT_ADMIN_NOTES_UPDATED, metadata__fulfillment_id=record.id).exists()


def test_invalid_fulfillment_transition_is_rejected_and_audited():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    record = create_fulfillment(seller=seller, winner=winner)
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.COMPLETED},
        format="json",
    )

    record.refresh_from_db()
    assert response.status_code == 400
    assert record.status == FulfillmentStatus.PENDING_CONFIRMATION
    assert AuditLog.objects.filter(
        action=AuditAction.FULFILLMENT_INVALID_TRANSITION,
        metadata__fulfillment_id=record.id,
        metadata__old_status=FulfillmentStatus.PENDING_CONFIRMATION,
        metadata__attempted_status=FulfillmentStatus.COMPLETED,
    ).exists()


def test_completed_and_cancelled_are_final_for_seller_status_changes():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    completed_record = create_fulfillment(seller=seller, winner=winner, title="Completed Lot")
    completed_record.status = FulfillmentStatus.COMPLETED
    completed_record.save(update_fields=("status", "updated_at"))
    cancelled_record = create_fulfillment(seller=seller, winner=winner, title="Cancelled Lot")
    cancelled_record.status = FulfillmentStatus.CANCELLED
    cancelled_record.save(update_fields=("status", "updated_at"))
    client = APIClient()
    client.force_authenticate(user=seller)

    completed_response = client.patch(
        f"/api/dashboard/fulfillment/{completed_record.id}/",
        {"status": FulfillmentStatus.SELLER_CONTACTED},
        format="json",
    )
    cancelled_response = client.patch(
        f"/api/dashboard/fulfillment/{cancelled_record.id}/",
        {"status": FulfillmentStatus.SELLER_CONTACTED},
        format="json",
    )

    completed_record.refresh_from_db()
    cancelled_record.refresh_from_db()
    assert completed_response.status_code == 400
    assert cancelled_response.status_code == 400
    assert completed_record.status == FulfillmentStatus.COMPLETED
    assert cancelled_record.status == FulfillmentStatus.CANCELLED


def test_disputed_can_move_to_allowed_resolution_status():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    record = create_fulfillment(seller=seller, winner=winner)
    record.status = FulfillmentStatus.DISPUTED
    record.save(update_fields=("status", "updated_at"))
    client = APIClient()
    client.force_authenticate(user=seller)

    response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.SELLER_CONTACTED},
        format="json",
    )

    record.refresh_from_db()
    assert response.status_code == 200
    assert record.status == FulfillmentStatus.SELLER_CONTACTED


def test_bidder_visible_notifications_are_scoped_and_safe():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    other_winner = create_user("other_winner")
    record = create_fulfillment(seller=seller, winner=winner)
    record.seller_notes = "Private seller note"
    record.admin_notes = "Private admin note"
    record.save(update_fields=("seller_notes", "admin_notes", "updated_at"))
    other_record = create_fulfillment(seller=seller, winner=other_winner, title="Other Winner Lot")
    client = APIClient()
    client.force_authenticate(user=seller)

    client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.SELLER_CONTACTED},
        format="json",
    )
    client.patch(
        f"/api/dashboard/fulfillment/{other_record.id}/",
        {"status": FulfillmentStatus.SELLER_CONTACTED},
        format="json",
    )

    client.force_authenticate(user=winner)
    response = client.get("/api/account/notifications/")

    assert response.status_code == 200
    assert len(response.data["results"]) == 1
    notification = response.data["results"][0]
    assert notification["notification_type"] == "seller_contacted"
    assert "Private seller note" not in notification["body"]
    assert "Private admin note" not in notification["body"]
    assert "recipient_email" not in notification
    assert OutboundNotification.objects.filter(recipient=other_winner).count() == 1


def test_fulfillment_timeline_permissions_and_public_safety():
    seller = create_user("seller", role=UserRole.SELLER)
    other_seller = create_user("other_seller", role=UserRole.SELLER)
    admin = create_user("admin", role=UserRole.ADMIN)
    winner = create_user("winner")
    record = create_fulfillment(seller=seller, winner=winner)
    client = APIClient()
    client.force_authenticate(user=seller)

    client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {
            "status": FulfillmentStatus.SELLER_CONTACTED,
            "seller_notes": "Private seller detail.",
            "public_winner_message": "Seller has contacted you.",
        },
        format="json",
    )
    seller_timeline = client.get(f"/api/dashboard/fulfillment/{record.id}/timeline/")

    client.force_authenticate(user=other_seller)
    other_timeline = client.get(f"/api/dashboard/fulfillment/{record.id}/timeline/")

    client.force_authenticate(user=admin)
    admin_timeline = client.get(f"/api/dashboard/fulfillment/{record.id}/timeline/")

    client.force_authenticate(user=winner)
    public_timeline = client.get(f"/api/account/won-lots/{record.id}/timeline/")

    assert seller_timeline.status_code == 200
    assert any(event["event_type"] == AuditAction.FULFILLMENT_STATUS_CHANGED for event in seller_timeline.data["results"])
    assert any(event["event_type"] == AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED for event in seller_timeline.data["results"])
    assert other_timeline.status_code == 404
    assert admin_timeline.status_code == 200
    assert public_timeline.status_code == 200
    public_events = public_timeline.data["results"]
    assert any(event["event_type"] == AuditAction.FULFILLMENT_STATUS_CHANGED for event in public_events)
    assert all(event["event_type"] != AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED for event in public_events)
    assert "Private seller detail." not in str(public_events)


def test_bidder_cannot_update_fulfillment_but_can_view_own_won_lots_without_private_notes():
    seller = create_user("seller", role=UserRole.SELLER)
    winner = create_user("winner")
    other_winner = create_user("other_winner")
    record = create_fulfillment(seller=seller, winner=winner)
    record.seller_notes = "Private seller note"
    record.admin_notes = "Private admin note"
    record.public_winner_message = "Collection details coming soon."
    record.save(update_fields=("seller_notes", "admin_notes", "public_winner_message", "updated_at"))
    create_fulfillment(seller=seller, winner=other_winner, title="Other Won Lot")

    client = APIClient()
    client.force_authenticate(user=winner)

    patch_response = client.patch(
        f"/api/dashboard/fulfillment/{record.id}/",
        {"status": FulfillmentStatus.COMPLETED},
        format="json",
    )
    won_response = client.get("/api/account/won-lots/")

    assert patch_response.status_code == 403
    assert won_response.status_code == 200
    assert len(won_response.data["results"]) == 1
    won_lot = won_response.data["results"][0]
    assert won_lot["lot_id"] == record.lot_id
    assert won_lot["public_winner_message"] == "Collection details coming soon."
    assert "seller_notes" not in won_lot
    assert "admin_notes" not in won_lot
