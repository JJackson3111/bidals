from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, FulfillmentRecord, Lot, LotStatus, LotWinnerStatus

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_ended_lot(*, seller, reserve_price=None):
    now = timezone.now()
    auction = Auction.objects.create(
        title="Legacy Auction",
        description="Ended auction missing winner repair data.",
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=1),
        status=AuctionStatus.ENDED,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title="Legacy Lot",
        description="Lot missing outcome fields.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        reserve_price=reserve_price,
        bid_increment=Decimal("10.00"),
        status=LotStatus.CLOSED,
    )
    return auction, lot


def run_command(*args):
    output = StringIO()
    call_command("backfill_winner_outcomes", *args, stdout=output)
    return output.getvalue()


def test_backfill_creates_missing_winner_outcome_and_fulfillment_record():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    _, lot = create_ended_lot(seller=seller, reserve_price=Decimal("120.00"))
    bid = Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=20),
    )

    output = run_command()

    lot.refresh_from_db()
    assert "repaired=1" in output
    assert lot.status == LotStatus.SOLD
    assert lot.winner == bidder
    assert lot.winning_bid == bid
    assert lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
    assert lot.winner_calculated_at is not None
    assert FulfillmentRecord.objects.filter(lot=lot, winner=bidder, winning_bid=bid).exists()
    assert AuditLog.objects.filter(action=AuditAction.WINNER_OUTCOME_BACKFILLED, metadata__lot_id=lot.id).exists()
    assert AuditLog.objects.filter(action=AuditAction.FULFILLMENT_CREATED, metadata__lot_id=lot.id).exists()


def test_backfill_is_idempotent_on_repeated_runs():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    _, lot = create_ended_lot(seller=seller)
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=20),
    )

    run_command()
    run_command()

    assert FulfillmentRecord.objects.filter(lot=lot).count() == 1
    assert AuditLog.objects.filter(action=AuditAction.WINNER_OUTCOME_BACKFILLED, metadata__lot_id=lot.id).count() == 1
    assert AuditLog.objects.filter(action=AuditAction.FULFILLMENT_CREATED, metadata__lot_id=lot.id).count() == 1


def test_backfill_records_no_bid_outcome_without_fulfillment():
    seller = create_user("seller", role=UserRole.SELLER)
    _, lot = create_ended_lot(seller=seller)

    run_command()

    lot.refresh_from_db()
    assert lot.winner_status == LotWinnerStatus.NO_BIDS
    assert lot.winner is None
    assert lot.winning_bid is None
    assert FulfillmentRecord.objects.filter(lot=lot).count() == 0


def test_backfill_records_reserve_not_met_outcome_without_fulfillment():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    _, lot = create_ended_lot(seller=seller, reserve_price=Decimal("150.00"))
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=20),
    )

    run_command()

    lot.refresh_from_db()
    assert lot.winner_status == LotWinnerStatus.RESERVE_NOT_MET
    assert lot.winner is None
    assert lot.winning_bid is None
    assert FulfillmentRecord.objects.filter(lot=lot).count() == 0


def test_backfill_dry_run_makes_no_changes():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    _, lot = create_ended_lot(seller=seller)
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=20),
    )

    output = run_command("--dry-run")

    lot.refresh_from_db()
    assert "dry_run=True" in output
    assert lot.winner_status == LotWinnerStatus.PENDING
    assert lot.winner is None
    assert lot.winning_bid is None
    assert FulfillmentRecord.objects.filter(lot=lot).count() == 0
    assert AuditLog.objects.filter(action=AuditAction.WINNER_OUTCOME_BACKFILLED, metadata__lot_id=lot.id).count() == 0
