from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, FulfillmentRecord, Lot, LotStatus, LotWinnerStatus
from apps.auctions.services.closing import close_expired_auctions

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_expired_auction(seller):
    now = timezone.now()
    return Auction.objects.create(
        title="Expired Auction",
        description="A live auction whose server end time has passed.",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(minutes=5),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )


def create_lot(*, auction, reserve_price=None):
    return Lot.objects.create(
        auction=auction,
        title="Finalizable Lot",
        description="A lot ready for winner calculation.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        reserve_price=reserve_price,
        bid_increment=Decimal("10.00"),
        status=LotStatus.OPEN,
    )


def test_close_expired_auction_transitions_status_and_assigns_winner():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction, reserve_price=Decimal("120.00"))
    bid = Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )

    results = close_expired_auctions()

    auction.refresh_from_db()
    lot.refresh_from_db()

    assert len(results) == 1
    assert results[0].transitioned is True
    assert auction.status == AuctionStatus.ENDED
    assert lot.status == LotStatus.SOLD
    assert lot.winner == bidder
    assert lot.winning_bid == bid
    assert lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
    assert lot.winner_calculated_at is not None
    assert AuditLog.objects.filter(action=AuditAction.AUCTION_ENDED, metadata__auction_id=auction.id).exists()
    assert AuditLog.objects.filter(action=AuditAction.WINNER_CALCULATED, metadata__winner_id=bidder.id).exists()
    assert FulfillmentRecord.objects.filter(lot=lot, winner=bidder, winning_bid=bid).exists()
    assert AuditLog.objects.filter(action=AuditAction.FULFILLMENT_CREATED, metadata__lot_id=lot.id).exists()
    assert AuditLog.objects.filter(action=AuditAction.NOTIFICATION_EVENT, metadata__event_type="winner_assigned").exists()


def test_close_expired_auction_records_no_bid_outcome():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction)

    close_expired_auctions()

    lot.refresh_from_db()
    assert lot.status == LotStatus.CLOSED
    assert lot.winner is None
    assert lot.winning_bid is None
    assert lot.winner_status == LotWinnerStatus.NO_BIDS
    assert AuditLog.objects.filter(
        action=AuditAction.WINNER_CALCULATED,
        metadata__lot_id=lot.id,
        metadata__winner_status=LotWinnerStatus.NO_BIDS,
    ).exists()


def test_close_expired_auction_records_reserve_not_met_outcome():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction, reserve_price=Decimal("150.00"))
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )

    close_expired_auctions()

    lot.refresh_from_db()
    assert lot.status == LotStatus.CLOSED
    assert lot.winner is None
    assert lot.winning_bid is None
    assert lot.winner_status == LotWinnerStatus.RESERVE_NOT_MET
    assert AuditLog.objects.filter(
        action=AuditAction.WINNER_CALCULATED,
        metadata__lot_id=lot.id,
        metadata__winner_status=LotWinnerStatus.RESERVE_NOT_MET,
        metadata__highest_amount="130.00",
    ).exists()


def test_close_expired_auction_is_idempotent_on_repeated_runs():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction)
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )

    close_expired_auctions()
    close_expired_auctions()

    lot.refresh_from_db()
    assert lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
    assert AuditLog.objects.filter(action=AuditAction.AUCTION_ENDED, metadata__auction_id=auction.id).count() == 1
    assert AuditLog.objects.filter(action=AuditAction.WINNER_CALCULATED, metadata__lot_id=lot.id).count() == 1
    assert FulfillmentRecord.objects.filter(lot=lot).count() == 1
    assert AuditLog.objects.filter(action=AuditAction.NOTIFICATION_EVENT, metadata__lot_id=lot.id).count() == 1
