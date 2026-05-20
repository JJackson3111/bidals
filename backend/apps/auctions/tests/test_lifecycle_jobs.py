from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Lot, LotStatus
from apps.auctions.services import lifecycle
from apps.auctions.services.lifecycle import (
    activate_scheduled_auction_if_due,
    get_effective_auction_status,
    get_effective_lot_status,
    is_lot_biddable,
    open_scheduled_auctions,
    sync_auction_lifecycle,
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


def create_scheduled_auction(*, seller, starts_delta, ends_delta):
    now = timezone.now()
    return Auction.objects.create(
        title="Scheduled Auction",
        description="A scheduled lifecycle test auction.",
        start_time=now + starts_delta,
        end_time=now + ends_delta,
        status=AuctionStatus.SCHEDULED,
        created_by=seller,
    )


def test_due_scheduled_auction_status_becomes_live_idempotently():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(minutes=1),
        ends_delta=timedelta(minutes=10),
    )

    first = activate_scheduled_auction_if_due(auction.id)
    second = activate_scheduled_auction_if_due(auction.id)

    auction.refresh_from_db()
    assert first.transitioned is True
    assert second.transitioned is False
    assert second.skipped_reason == "already_live"
    assert auction.status == AuctionStatus.LIVE
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_UPDATED,
        metadata__auction_id=auction.id,
        metadata__lifecycle_event="auction_activated",
    ).count() == 1


def test_open_scheduled_auctions_skips_not_yet_due_and_expired_scheduled_auctions():
    seller = create_user("seller", role=UserRole.SELLER)
    due = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(minutes=1),
        ends_delta=timedelta(minutes=10),
    )
    not_due = create_scheduled_auction(
        seller=seller,
        starts_delta=timedelta(minutes=5),
        ends_delta=timedelta(minutes=15),
    )
    expired = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(minutes=20),
        ends_delta=-timedelta(minutes=1),
    )

    results = open_scheduled_auctions()

    due.refresh_from_db()
    not_due.refresh_from_db()
    expired.refresh_from_db()
    assert [result.auction_id for result in results] == [due.id]
    assert due.status == AuctionStatus.LIVE
    assert not_due.status == AuctionStatus.SCHEDULED
    assert expired.status == AuctionStatus.SCHEDULED


@pytest.mark.parametrize("stored_status", ["open", "Scheduled"])
def test_open_scheduled_auctions_normalizes_staging_like_status_values(stored_status):
    seller = create_user(f"seller_{stored_status.lower()}", role=UserRole.SELLER)
    now = timezone.now()
    auction = Auction.objects.create(
        title=f"Staging status {stored_status}",
        description="A due auction using a legacy or display-cased staging status value.",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(minutes=10),
        status=stored_status,
        created_by=seller,
    )

    results = open_scheduled_auctions(now=now)

    auction.refresh_from_db()
    assert [result.auction_id for result in results] == [auction.id]
    assert results[0].transitioned is True
    assert auction.status == AuctionStatus.LIVE
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_OPENED_AUTOMATICALLY,
        metadata__auction_id=auction.id,
        metadata__previous_status=stored_status,
        metadata__new_status=AuctionStatus.LIVE,
    ).count() == 1


def test_open_scheduled_auctions_handles_utc_aware_timestamps():
    seller = create_user("seller_utc", role=UserRole.SELLER)
    now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
    auction = Auction.objects.create(
        title="UTC Scheduled Auction",
        description="A due scheduled auction with explicit UTC timestamps.",
        start_time=now - timedelta(seconds=1),
        end_time=now + timedelta(minutes=10),
        status=AuctionStatus.SCHEDULED,
        created_by=seller,
    )

    results = open_scheduled_auctions(now=now)

    auction.refresh_from_db()
    assert timezone.is_aware(auction.start_time)
    assert [result.auction_id for result in results] == [auction.id]
    assert auction.status == AuctionStatus.LIVE


def test_open_scheduled_auctions_command_is_idempotent(capsys):
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(minutes=1),
        ends_delta=timedelta(minutes=10),
    )

    call_command("open_scheduled_auctions")
    call_command("open_scheduled_auctions")

    auction.refresh_from_db()
    output = capsys.readouterr().out
    assert auction.status == AuctionStatus.LIVE
    assert "Due auctions found: 1; opened 1; skipped 0." in output
    assert "Due auctions found: 0; opened 0; skipped 0." in output
    assert "opened 1" in output
    assert "opened 0" in output
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_UPDATED,
        metadata__auction_id=auction.id,
        metadata__lifecycle_event="auction_activated",
    ).count() == 1


def test_effective_status_uses_aware_backend_timestamps_not_stored_scheduled_state():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    auction = Auction.objects.create(
        title="Backend Time Auction",
        description="Stored as scheduled but already in its bidding window.",
        start_time=now - timedelta(minutes=2),
        end_time=now + timedelta(minutes=20),
        status=AuctionStatus.SCHEDULED,
        created_by=seller,
    )
    lot = Lot.objects.create(
        auction=auction,
        title="Backend Time Lot",
        description="Biddable by effective server state.",
        starting_price="10.00",
        current_price="10.00",
        bid_increment="5.00",
        status=LotStatus.OPEN,
    )

    assert timezone.is_aware(now)
    assert get_effective_auction_status(auction, now=now) == AuctionStatus.LIVE
    assert get_effective_lot_status(lot, now=now) == LotStatus.OPEN
    assert is_lot_biddable(lot, now=now) is True


def test_sync_auction_lifecycle_twice_creates_one_open_audit_record():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(minutes=1),
        ends_delta=timedelta(minutes=10),
    )

    first = sync_auction_lifecycle(auction.id)
    second = sync_auction_lifecycle(auction.id)

    auction.refresh_from_db()
    assert first.transitioned is True
    assert second.transitioned is False
    assert auction.status == AuctionStatus.LIVE
    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_OPENED_AUTOMATICALLY,
        metadata__auction_id=auction.id,
    ).count() == 1


def test_lifecycle_close_job_continues_after_one_record_failure(monkeypatch):
    seller = create_user("seller", role=UserRole.SELLER)
    good = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(hours=2),
        ends_delta=-timedelta(minutes=30),
    )
    broken = create_scheduled_auction(
        seller=seller,
        starts_delta=-timedelta(hours=2),
        ends_delta=-timedelta(minutes=20),
    )
    original_sync = lifecycle.sync_auction_lifecycle

    def flaky_sync(auction_id, now=None):
        if auction_id == broken.id:
            raise RuntimeError("simulated partial failure")
        return original_sync(auction_id, now=now)

    monkeypatch.setattr(lifecycle, "sync_auction_lifecycle", flaky_sync)

    results = lifecycle.close_due_auctions(now=timezone.now())

    good.refresh_from_db()
    broken.refresh_from_db()
    assert [result.auction_id for result in results] == [good.id]
    assert good.status == AuctionStatus.ENDED
    assert broken.status == AuctionStatus.SCHEDULED
    assert AuditLog.objects.filter(
        action=AuditAction.JOB_FAILED,
        entity_id=str(broken.id),
        metadata__job_name="close_due_auctions",
    ).exists()
