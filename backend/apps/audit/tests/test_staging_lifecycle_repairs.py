from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
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


def create_effectively_ended_live_auction(*, seller):
    now = timezone.now()
    return Auction.objects.create(
        title="Ended But Stored Live",
        description="A staging auction whose stored lifecycle state is stale.",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(minutes=10),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )


def create_sold_lot_missing_winner(*, auction):
    return Lot.objects.create(
        auction=auction,
        title="Sold Lot Missing Winner",
        description="A staging sold lot missing winner pointers.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        bid_increment=Decimal("5.00"),
        status=LotStatus.SOLD,
        winner=None,
        winning_bid=None,
        winner_status=LotWinnerStatus.PENDING,
    )


def test_staging_repair_lifecycle_issues_dry_run_writes_nothing(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_NAME", raising=False)
    seller = create_user("dry_seller", role=UserRole.SELLER)
    bidder = create_user("dry_bidder")
    auction = create_effectively_ended_live_auction(seller=seller)
    lot = create_sold_lot_missing_winner(auction=auction)
    Bid.objects.create(lot=lot, bidder=bidder, amount=Decimal("125.00"), status=BidStatus.ACCEPTED)
    before = repair_snapshot()
    output = StringIO()

    call_command("staging_repair_lifecycle_issues", stdout=output)

    rendered = output.getvalue()
    assert "mode=dry-run" in rendered
    assert "No data was modified." in rendered
    assert "set_auction_status_ended" in rendered
    assert "set_sold_lot_winner_from_highest_accepted_bid" in rendered
    assert repair_snapshot() == before


def test_staging_repair_lifecycle_issues_apply_refuses_non_staging(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "bidals-backend")
    seller = create_user("guard_seller", role=UserRole.SELLER)
    auction = create_effectively_ended_live_auction(seller=seller)
    before = repair_snapshot()

    with pytest.raises(CommandError, match="allowed only"):
        call_command("staging_repair_lifecycle_issues", apply=True)

    auction.refresh_from_db()
    assert auction.status == AuctionStatus.LIVE
    assert repair_snapshot() == before


def test_staging_repair_lifecycle_issues_repairs_sold_lot_missing_winner(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "bidals-backend")
    seller = create_user("winner_seller", role=UserRole.SELLER)
    low_bidder = create_user("low_bidder")
    high_bidder = create_user("high_bidder")
    auction = create_effectively_ended_live_auction(seller=seller)
    lot = create_sold_lot_missing_winner(auction=auction)
    low_bid = Bid.objects.create(lot=lot, bidder=low_bidder, amount=Decimal("125.00"), status=BidStatus.ACCEPTED)
    high_bid = Bid.objects.create(lot=lot, bidder=high_bidder, amount=Decimal("150.00"), status=BidStatus.ACCEPTED)
    output = StringIO()

    call_command("staging_repair_lifecycle_issues", apply=True, stdout=output)

    lot.refresh_from_db()
    low_bid.refresh_from_db()
    high_bid.refresh_from_db()
    assert lot.status == LotStatus.SOLD
    assert lot.winning_bid == high_bid
    assert lot.winner == high_bidder
    assert lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
    assert low_bid.amount == Decimal("125.00")
    assert high_bid.amount == Decimal("150.00")
    assert AuditLog.objects.filter(
        action=AuditAction.ADMIN_ACTION,
        entity_type="lot",
        entity_id=str(lot.id),
        metadata__source="staging_repair_lifecycle_issues",
        metadata__repair_action="set_sold_lot_winner_from_highest_accepted_bid",
    ).exists()
    assert "winner_seller@example.com" not in output.getvalue()


def test_staging_repair_lifecycle_issues_repairs_live_stored_ended_effective_auction(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    seller = create_user("auction_seller", role=UserRole.SELLER)
    auction = create_effectively_ended_live_auction(seller=seller)

    call_command("staging_repair_lifecycle_issues", apply=True)

    auction.refresh_from_db()
    assert auction.status == AuctionStatus.ENDED
    assert AuditLog.objects.filter(
        action=AuditAction.ADMIN_ACTION,
        entity_type="auction",
        entity_id=str(auction.id),
        metadata__source="staging_repair_lifecycle_issues",
        metadata__repair_action="set_auction_status_ended",
    ).exists()


def test_staging_repair_lifecycle_issues_is_idempotent(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    seller = create_user("idempotent_seller", role=UserRole.SELLER)
    bidder = create_user("idempotent_bidder")
    auction = create_effectively_ended_live_auction(seller=seller)
    lot = create_sold_lot_missing_winner(auction=auction)
    Bid.objects.create(lot=lot, bidder=bidder, amount=Decimal("125.00"), status=BidStatus.ACCEPTED)
    first_output = StringIO()
    second_output = StringIO()

    call_command("staging_repair_lifecycle_issues", apply=True, stdout=first_output)
    after_first = repair_snapshot()
    audit_count_after_first = AuditLog.objects.filter(metadata__source="staging_repair_lifecycle_issues").count()
    call_command("staging_repair_lifecycle_issues", apply=True, stdout=second_output)

    assert "applied=2" in first_output.getvalue()
    assert "applied=0" in second_output.getvalue()
    assert repair_snapshot() == after_first
    assert AuditLog.objects.filter(metadata__source="staging_repair_lifecycle_issues").count() == audit_count_after_first


def test_staging_repair_lifecycle_issues_does_not_create_winner_without_valid_bid(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    seller = create_user("no_bid_seller", role=UserRole.SELLER)
    rejected_bidder = create_user("rejected_bidder")
    auction = create_effectively_ended_live_auction(seller=seller)
    lot = create_sold_lot_missing_winner(auction=auction)
    Bid.objects.create(
        lot=lot,
        bidder=rejected_bidder,
        amount=Decimal("125.00"),
        status=BidStatus.REJECTED,
    )
    output = StringIO()

    call_command("staging_repair_lifecycle_issues", apply=True, stdout=output)

    lot.refresh_from_db()
    assert lot.winner_id is None
    assert lot.winning_bid_id is None
    assert lot.winner_status == LotWinnerStatus.PENDING
    assert "reason=no_valid_accepted_bid" in output.getvalue()
    assert not AuditLog.objects.filter(
        entity_type="lot",
        entity_id=str(lot.id),
        metadata__source="staging_repair_lifecycle_issues",
    ).exists()


def repair_snapshot():
    return {
        "auctions": list(Auction.objects.order_by("id").values("id", "status", "updated_at")),
        "lots": list(
            Lot.objects.order_by("id").values(
                "id",
                "status",
                "winner_id",
                "winning_bid_id",
                "winner_status",
                "updated_at",
            )
        ),
        "bids": list(Bid.objects.order_by("id").values("id", "amount", "status", "bidder_id")),
        "audit_count": AuditLog.objects.count(),
    }
