from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import threading

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections, connections
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidRejectionReason,
    BidStatus,
    Lot,
    LotStatus,
)
from apps.auctions.services.bidding import place_bid

pytestmark = pytest.mark.django_db(transaction=True)

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def create_auction(*, seller, status=AuctionStatus.LIVE, starts_at=None, ends_at=None):
    now = timezone.now()
    return Auction.objects.create(
        title="Rare Collectibles",
        description="A live auction.",
        start_time=starts_at or now - timedelta(minutes=5),
        end_time=ends_at or now + timedelta(minutes=5),
        status=status,
        created_by=seller,
    )


def create_lot(*, auction, status=LotStatus.OPEN, current_price=Decimal("90.00"), increment=Decimal("10.00")):
    return Lot.objects.create(
        auction=auction,
        title="Lot 1",
        description="A test lot.",
        starting_price=current_price,
        current_price=current_price,
        bid_increment=increment,
        status=status,
    )


def live_lot():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)
    lot = create_lot(auction=auction)
    return seller, auction, lot


def test_accepts_valid_bid_and_updates_lot_price():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("100.00"))

    lot.refresh_from_db()
    bid = Bid.objects.get(lot=lot, bidder=bidder)

    assert result.accepted is True
    assert result.bid_id == bid.id
    assert bid.status == BidStatus.ACCEPTED
    assert lot.current_price == Decimal("100.00")


def test_rejects_bid_below_current_price():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("80.00"))

    lot.refresh_from_db()
    bid = Bid.objects.get(lot=lot, bidder=bidder)

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.BID_TOO_LOW
    assert bid.status == BidStatus.REJECTED
    assert bid.rejection_reason == BidRejectionReason.BID_TOO_LOW
    assert lot.current_price == Decimal("90.00")


def test_rejects_bid_with_invalid_increment():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("105.00"))

    lot.refresh_from_db()
    bid = Bid.objects.get(lot=lot, bidder=bidder)

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.INVALID_INCREMENT
    assert bid.rejection_reason == BidRejectionReason.INVALID_INCREMENT
    assert lot.current_price == Decimal("90.00")


def test_rejects_bid_before_auction_start():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    auction = create_auction(
        seller=seller,
        starts_at=now + timedelta(minutes=10),
        ends_at=now + timedelta(minutes=20),
    )
    lot = create_lot(auction=auction)
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("100.00"))

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.AUCTION_NOT_LIVE


def test_rejects_bid_after_auction_end():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    auction = create_auction(
        seller=seller,
        starts_at=now - timedelta(minutes=20),
        ends_at=now - timedelta(minutes=10),
    )
    lot = create_lot(auction=auction)
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("100.00"))

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.AUCTION_NOT_LIVE


def test_rejects_bid_on_closed_lot():
    _, auction, _ = live_lot()
    lot = create_lot(auction=auction, status=LotStatus.CLOSED)
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("100.00"))

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.LOT_CLOSED


def test_rejects_unauthenticated_bid():
    _, _, lot = live_lot()

    result = place_bid(AnonymousUser(), lot.id, Decimal("100.00"))

    assert result.status == BidStatus.REJECTED
    assert result.reason == BidRejectionReason.UNAUTHENTICATED
    assert Bid.objects.filter(lot=lot).count() == 0
    assert AuditLog.objects.filter(action=AuditAction.BID_REJECTED, metadata__reason=BidRejectionReason.UNAUTHENTICATED).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED_SECURITY,
        metadata__reason=BidRejectionReason.UNAUTHENTICATED,
    ).exists()


def test_creates_audit_log_for_accepted_bid():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("100.00"))

    audit = AuditLog.objects.get(action=AuditAction.BID_ACCEPTED, entity_id=str(result.bid_id))
    assert audit.actor == bidder
    assert audit.metadata["lot_id"] == lot.id
    assert audit.metadata["bidder_id"] == bidder.id
    assert audit.metadata["previous_price"] == "90.00"
    assert audit.metadata["new_price"] == "100.00"


def test_creates_audit_log_for_rejected_bid():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    result = place_bid(bidder, lot.id, Decimal("80.00"))

    audit = AuditLog.objects.get(action=AuditAction.BID_REJECTED, entity_id=str(result.bid_id))
    assert audit.actor == bidder
    assert audit.metadata["lot_id"] == lot.id
    assert audit.metadata["bidder_id"] == bidder.id
    assert audit.metadata["attempted_amount"] == "80.00"
    assert audit.metadata["current_price"] == "90.00"
    assert audit.metadata["reason"] == BidRejectionReason.BID_TOO_LOW
    assert AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED_VALIDATION,
        entity_id=str(result.bid_id),
        metadata__reason=BidRejectionReason.BID_TOO_LOW,
    ).exists()


def test_lot_price_updates_only_after_accepted_bid():
    _, _, lot = live_lot()
    bidder = create_user("bidder")

    rejected = place_bid(bidder, lot.id, Decimal("95.00"))
    lot.refresh_from_db()
    assert rejected.status == BidStatus.REJECTED
    assert lot.current_price == Decimal("90.00")

    accepted = place_bid(bidder, lot.id, Decimal("100.00"))
    lot.refresh_from_db()
    assert accepted.status == BidStatus.ACCEPTED
    assert lot.current_price == Decimal("100.00")


def test_concurrent_bidding_uses_locked_current_price_and_prevents_lower_overwrite():
    _, _, lot = live_lot()
    lower_bidder = create_user("lower_bidder")
    higher_bidder = create_user("higher_bidder")
    barrier = threading.Barrier(2)

    def bid_in_thread(user_id, amount):
        close_old_connections()
        try:
            user = User.objects.get(pk=user_id)
            barrier.wait(timeout=10)
            return place_bid(user, lot.id, Decimal(amount))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        lower_future = executor.submit(bid_in_thread, lower_bidder.id, "100.00")
        higher_future = executor.submit(bid_in_thread, higher_bidder.id, "110.00")
        results = [lower_future.result(timeout=20), higher_future.result(timeout=20)]

    connections.close_all()

    lot.refresh_from_db()
    accepted_bids = Bid.objects.filter(lot=lot, status=BidStatus.ACCEPTED).order_by("server_timestamp")
    higher_bid = accepted_bids.get(amount=Decimal("110.00"))
    lower_accepted_after_higher = accepted_bids.filter(
        amount=Decimal("100.00"),
        server_timestamp__gt=higher_bid.server_timestamp,
    ).exists()

    assert any(result.accepted for result in results)
    assert lot.current_price == Decimal("110.00")
    assert higher_bid.bidder == higher_bidder
    assert lower_accepted_after_higher is False
