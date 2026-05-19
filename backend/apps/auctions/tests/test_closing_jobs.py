from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog, OutboundNotification
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


def create_expired_auction(seller, *, status=AuctionStatus.LIVE):
    now = timezone.now()
    return Auction.objects.create(
        title="Expired Auction",
        description="A live auction whose server end time has passed.",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(minutes=5),
        status=status,
        created_by=seller,
    )


def create_live_auction(seller):
    now = timezone.now()
    return Auction.objects.create(
        title="Live Auction",
        description="A live auction whose server end time is still in the future.",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(hours=1),
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
    assert OutboundNotification.objects.filter(
        recipient=bidder,
        notification_type="winner_assigned",
        related_entity_type="lot",
        related_entity_id=str(lot.id),
    ).exists()


def test_expired_scheduled_auction_is_finalized_from_server_time():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_expired_auction(seller, status=AuctionStatus.SCHEDULED)
    lot = create_lot(auction=auction)
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
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_ENDED,
        metadata__auction_id=auction.id,
        metadata__previous_status=AuctionStatus.SCHEDULED,
    ).exists()


def test_expired_legacy_open_auction_is_finalized_from_server_time():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_expired_auction(seller, status="open")
    lot = create_lot(auction=auction)

    results = close_expired_auctions()

    auction.refresh_from_db()
    lot.refresh_from_db()
    assert len(results) == 1
    assert results[0].transitioned is True
    assert auction.status == AuctionStatus.ENDED
    assert lot.status == LotStatus.CLOSED
    assert lot.winner_status == LotWinnerStatus.NO_BIDS
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_ENDED,
        metadata__auction_id=auction.id,
        metadata__previous_status="open",
    ).exists()


def test_highest_accepted_bid_wins_even_when_rejected_bid_is_higher():
    seller = create_user("seller", role=UserRole.SELLER)
    low_bidder = create_user("low_bidder")
    high_bidder = create_user("high_bidder")
    rejected_bidder = create_user("rejected_bidder")
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction)
    low_bid = Bid.objects.create(
        lot=lot,
        bidder=low_bidder,
        amount=Decimal("120.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=3),
    )
    high_bid = Bid.objects.create(
        lot=lot,
        bidder=high_bidder,
        amount=Decimal("150.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=2),
    )
    rejected_bid = Bid.objects.create(
        lot=lot,
        bidder=rejected_bidder,
        amount=Decimal("200.00"),
        status=BidStatus.REJECTED,
        server_timestamp=timezone.now() - timedelta(minutes=1),
    )

    close_expired_auctions()

    lot.refresh_from_db()
    assert lot.winner == high_bidder
    assert lot.winning_bid == high_bid
    assert lot.winning_bid != low_bid
    assert lot.winning_bid != rejected_bid


def test_won_lots_endpoint_and_bidder_notification_show_closed_winning_lot():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    other_bidder = create_user("other_bidder")
    auction = create_expired_auction(seller)
    lot = create_lot(auction=auction)
    bid = Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )
    Bid.objects.create(
        lot=lot,
        bidder=other_bidder,
        amount=Decimal("120.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now() - timedelta(minutes=1),
    )

    close_expired_auctions()

    lot.refresh_from_db()
    record = FulfillmentRecord.objects.get(lot=lot)
    client = APIClient()
    client.force_authenticate(user=bidder)
    won_response = client.get("/api/account/won-lots/")
    notification_response = client.get("/api/account/notifications/")

    assert won_response.status_code == 200
    assert len(won_response.data["results"]) == 1
    won_lot = won_response.data["results"][0]
    assert won_lot["id"] == record.id
    assert won_lot["auction_id"] == auction.id
    assert won_lot["lot_id"] == lot.id
    assert won_lot["winning_bid"] == bid.id
    assert won_lot["winning_bid_amount"] == "130.00"
    assert won_lot["outcome_status"] == LotWinnerStatus.WINNER_ASSIGNED
    assert won_lot["fulfillment_status"] == "pending_confirmation"
    assert won_lot["date_won"] is not None
    assert notification_response.status_code == 200
    assert notification_response.data["unread_count"] == 1
    assert notification_response.data["results"][0]["notification_type"] == "winner_assigned"


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
    assert OutboundNotification.objects.filter(
        recipient=bidder,
        notification_type="winner_assigned",
        related_entity_type="lot",
        related_entity_id=str(lot.id),
    ).count() == 1


def test_close_expired_auction_repairs_missing_fulfillment_without_recalculating_winner():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_expired_auction(seller)
    auction.status = AuctionStatus.ENDED
    auction.save(update_fields=("status", "updated_at"))
    lot = create_lot(auction=auction)
    bid = Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )
    lot.status = LotStatus.SOLD
    lot.winner = bidder
    lot.winning_bid = bid
    lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
    lot.winner_calculated_at = timezone.now() - timedelta(minutes=2)
    lot.save(update_fields=("status", "winner", "winning_bid", "winner_status", "winner_calculated_at", "updated_at"))

    results = close_expired_auctions()

    assert len(results) == 1
    assert results[0].transitioned is False
    assert FulfillmentRecord.objects.filter(lot=lot, winner=bidder, winning_bid=bid).count() == 1
    assert AuditLog.objects.filter(action=AuditAction.WINNER_CALCULATED, metadata__lot_id=lot.id).count() == 0
    assert OutboundNotification.objects.filter(
        recipient=bidder,
        notification_type="winner_assigned",
        related_entity_type="lot",
        related_entity_id=str(lot.id),
    ).count() == 1


def test_non_expired_live_auction_remains_live_and_open():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder")
    auction = create_live_auction(seller)
    lot = create_lot(auction=auction)
    Bid.objects.create(
        lot=lot,
        bidder=bidder,
        amount=Decimal("130.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )

    results = close_expired_auctions()

    auction.refresh_from_db()
    lot.refresh_from_db()
    assert results == []
    assert auction.status == AuctionStatus.LIVE
    assert lot.status == LotStatus.OPEN
    assert lot.winner is None
    assert lot.winning_bid is None
    assert lot.winner_calculated_at is None
