from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
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
    OutcomeRepairComment,
    OutcomeRepairRequest,
    OutcomeRepairStatus,
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


def create_repair_fixture():
    now = timezone.now()
    seller = create_user("seller", role=UserRole.SELLER)
    old_winner = create_user("old_winner")
    new_winner = create_user("new_winner")
    auction = Auction.objects.create(
        title="Repair Auction",
        description="Ended auction with an exceptional correction.",
        start_time=now - timedelta(hours=4),
        end_time=now - timedelta(hours=2),
        status=AuctionStatus.ENDED,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title="Repair Lot",
        description="Lot with finalized outcome.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("150.00"),
        reserve_price=Decimal("100.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.SOLD,
        winner=old_winner,
        winner_status=LotWinnerStatus.WINNER_ASSIGNED,
        winner_calculated_at=now - timedelta(hours=1),
    )
    old_bid = Bid.objects.create(
        lot=lot,
        bidder=old_winner,
        amount=Decimal("140.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=now - timedelta(hours=2),
    )
    new_bid = Bid.objects.create(
        lot=lot,
        bidder=new_winner,
        amount=Decimal("150.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=now - timedelta(hours=2, minutes=1),
    )
    lot.winning_bid = old_bid
    lot.save(update_fields=("winning_bid",))
    FulfillmentRecord.objects.create(
        lot=lot,
        auction=auction,
        winning_bid=old_bid,
        winner=old_winner,
        status=FulfillmentStatus.SELLER_CONTACTED,
        seller_notes="Private existing note.",
    )
    return seller, old_winner, new_winner, lot, old_bid, new_bid


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_admin_can_create_approve_and_apply_repair_without_altering_bids():
    requester = create_user("admin_requester", role=UserRole.ADMIN)
    approver = create_user("admin_approver", role=UserRole.ADMIN)
    _, old_winner, new_winner, lot, old_bid, new_bid = create_repair_fixture()
    requester_client = authenticated_client(requester)
    approver_client = authenticated_client(approver)

    create_response = requester_client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": new_bid.id, "reason": "Correct accepted bid selected."},
        format="json",
    )
    repair_id = create_response.data["id"]
    apply_before_approval = approver_client.post(f"/api/admin/outcome-repairs/{repair_id}/apply/")
    self_approve_response = requester_client.post(f"/api/admin/outcome-repairs/{repair_id}/approve/")
    approve_response = approver_client.post(
        f"/api/admin/outcome-repairs/{repair_id}/approve/",
        {"approval_notes": "Reviewed against accepted bid history."},
        format="json",
    )
    apply_response = approver_client.post(f"/api/admin/outcome-repairs/{repair_id}/apply/")
    apply_again_response = approver_client.post(f"/api/admin/outcome-repairs/{repair_id}/apply/")

    lot.refresh_from_db()
    old_bid.refresh_from_db()
    new_bid.refresh_from_db()
    fulfillment = FulfillmentRecord.objects.get(lot=lot)
    repair = OutcomeRepairRequest.objects.get(pk=repair_id)

    assert create_response.status_code == 201
    assert apply_before_approval.status_code == 400
    assert self_approve_response.status_code == 400
    assert approve_response.status_code == 200
    assert apply_response.status_code == 200
    assert apply_again_response.status_code == 400
    assert repair.status == OutcomeRepairStatus.APPLIED
    assert repair.reviewed_by == approver
    assert repair.approval_notes == "Reviewed against accepted bid history."
    assert lot.winner == new_winner
    assert lot.winning_bid == new_bid
    assert lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
    assert lot.status == LotStatus.SOLD
    assert old_bid.status == BidStatus.ACCEPTED
    assert new_bid.status == BidStatus.ACCEPTED
    assert fulfillment.winner == new_winner
    assert fulfillment.winning_bid == new_bid
    assert fulfillment.status == FulfillmentStatus.PENDING_CONFIRMATION
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_REQUESTED, metadata__repair_id=repair_id).exists()
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_INVALID_APPROVAL, metadata__repair_id=repair_id).exists()
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_APPROVED, metadata__repair_id=repair_id).exists()
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_APPLIED, metadata__repair_id=repair_id).exists()
    assert AuditLog.objects.filter(action=AuditAction.NOTIFICATION_EVENT, metadata__event_type="outcome_repair_applied").exists()


def test_non_admin_cannot_create_repair_request():
    seller, _, _, lot, _, new_bid = create_repair_fixture()
    client = authenticated_client(seller)

    response = client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": new_bid.id, "reason": "Seller should not be allowed."},
        format="json",
    )

    assert response.status_code == 403


def test_repair_requires_reason_and_valid_accepted_bid_for_lot():
    admin = create_user("admin", role=UserRole.ADMIN)
    _, _, other_winner, lot, _, _ = create_repair_fixture()
    other_lot = Lot.objects.create(
        auction=lot.auction,
        title="Other Lot",
        description="Different lot.",
        starting_price=Decimal("10.00"),
        current_price=Decimal("10.00"),
        bid_increment=Decimal("1.00"),
        status=LotStatus.CLOSED,
    )
    wrong_lot_bid = Bid.objects.create(
        lot=other_lot,
        bidder=other_winner,
        amount=Decimal("20.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )
    rejected_bid = Bid.objects.create(
        lot=lot,
        bidder=other_winner,
        amount=Decimal("160.00"),
        status=BidStatus.REJECTED,
        server_timestamp=timezone.now(),
    )
    client = authenticated_client(admin)

    missing_reason = client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": wrong_lot_bid.id, "reason": ""},
        format="json",
    )
    wrong_lot_response = client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": wrong_lot_bid.id, "reason": "Wrong lot."},
        format="json",
    )
    rejected_bid_response = client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": rejected_bid.id, "reason": "Rejected bid."},
        format="json",
    )

    assert missing_reason.status_code == 400
    assert wrong_lot_response.status_code == 400
    assert rejected_bid_response.status_code == 400


def test_rejected_repair_cannot_be_applied():
    admin = create_user("admin", role=UserRole.ADMIN)
    _, _, _, lot, _, new_bid = create_repair_fixture()
    client = authenticated_client(admin)
    repair = client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": new_bid.id, "reason": "Reject this."},
        format="json",
    )

    reject_response = client.post(f"/api/admin/outcome-repairs/{repair.data['id']}/reject/")
    apply_response = client.post(f"/api/admin/outcome-repairs/{repair.data['id']}/apply/")

    assert reject_response.status_code == 200
    assert reject_response.data["status"] == OutcomeRepairStatus.REJECTED
    assert apply_response.status_code == 400
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_REJECTED, metadata__repair_id=repair.data["id"]).exists()


def test_admin_repair_comments_are_admin_only_ordered_and_audited():
    requester = create_user("comment_requester", role=UserRole.ADMIN)
    other_admin = create_user("comment_admin", role=UserRole.ADMIN)
    bidder = create_user("comment_bidder", role=UserRole.BIDDER)
    _, _, _, lot, _, new_bid = create_repair_fixture()
    requester_client = authenticated_client(requester)
    other_admin_client = authenticated_client(other_admin)
    bidder_client = authenticated_client(bidder)

    repair_response = requester_client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": new_bid.id, "reason": "Needs discussion."},
        format="json",
    )
    repair_id = repair_response.data["id"]

    first_comment = requester_client.post(
        f"/api/admin/outcome-repairs/{repair_id}/comments/",
        {"comment_text": "Initial evidence attached in ops notes."},
        format="json",
    )
    second_comment = other_admin_client.post(
        f"/api/admin/outcome-repairs/{repair_id}/comments/",
        {"comment_text": "Reviewed accepted bids; approval can proceed."},
        format="json",
    )
    bidder_comment = bidder_client.post(
        f"/api/admin/outcome-repairs/{repair_id}/comments/",
        {"comment_text": "I should not be here."},
        format="json",
    )
    list_response = other_admin_client.get(f"/api/admin/outcome-repairs/{repair_id}/comments/")

    assert first_comment.status_code == 201
    assert second_comment.status_code == 201
    assert bidder_comment.status_code == 403
    assert list_response.status_code == 200
    assert [comment["comment_text"] for comment in list_response.data["results"]] == [
        "Initial evidence attached in ops notes.",
        "Reviewed accepted bids; approval can proceed.",
    ]
    assert OutcomeRepairComment.objects.filter(repair_request_id=repair_id).count() == 2
    assert AuditLog.objects.filter(
        action=AuditAction.OUTCOME_REPAIR_COMMENT_CREATED,
        metadata__repair_id=repair_id,
    ).count() == 2


def test_repair_audit_detail_is_admin_only_chronological_and_sanitized():
    requester = create_user("audit_requester", role=UserRole.ADMIN)
    approver = create_user("audit_approver", role=UserRole.ADMIN)
    seller = create_user("audit_seller", role=UserRole.SELLER)
    _, _, _, lot, _, new_bid = create_repair_fixture()
    requester_client = authenticated_client(requester)
    approver_client = authenticated_client(approver)
    seller_client = authenticated_client(seller)

    repair_response = requester_client.post(
        "/api/admin/outcome-repairs/",
        {"lot": lot.id, "requested_winning_bid": new_bid.id, "reason": "Review audit history."},
        format="json",
    )
    repair_id = repair_response.data["id"]
    requester_client.post(
        f"/api/admin/outcome-repairs/{repair_id}/comments/",
        {"comment_text": "Evidence reviewed."},
        format="json",
    )
    approver_client.post(f"/api/admin/outcome-repairs/{repair_id}/approve/", format="json")
    AuditLog.objects.create(
        actor=approver,
        action=AuditAction.ADMIN_ACTION,
        entity_type="outcome_repair",
        entity_id=str(repair_id),
        metadata={"repair_id": repair_id, "password": "should-not-leak", "safe": "visible"},
    )

    seller_response = seller_client.get(f"/api/admin/outcome-repairs/{repair_id}/audit/")
    admin_response = approver_client.get(f"/api/admin/outcome-repairs/{repair_id}/audit/")

    assert seller_response.status_code == 403
    assert admin_response.status_code == 200
    events = admin_response.data["results"]
    timestamps = [event["server_timestamp"] for event in events]
    assert timestamps == sorted(timestamps)
    actions = [event["action"] for event in events]
    assert AuditAction.OUTCOME_REPAIR_REQUESTED in actions
    assert AuditAction.OUTCOME_REPAIR_COMMENT_CREATED in actions
    assert AuditAction.OUTCOME_REPAIR_APPROVED in actions
    admin_action = next(event for event in events if event["action"] == AuditAction.ADMIN_ACTION)
    assert admin_action["metadata"]["password"] == "[REDACTED]"
    assert admin_action["metadata"]["safe"] == "visible"
    assert AuditLog.objects.filter(action=AuditAction.OUTCOME_REPAIR_AUDIT_VIEWED, metadata__repair_id=repair_id).exists()
