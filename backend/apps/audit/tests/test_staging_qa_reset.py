import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.audit.services.staging_qa_reset import QA_BASELINE_AUCTION_TITLE, reset_summary
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


def allow_staging(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("BIDALS_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)


def create_user(username, *, role=UserRole.BIDDER, is_superuser=False):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
        is_staff=is_superuser,
        is_superuser=is_superuser,
    )


def create_qa_auction(*, seller, title="QA- Old Lifecycle Cleanup", status=AuctionStatus.ENDED):
    now = timezone.now()
    return Auction.objects.create(
        title=title,
        description="Temporary QA lifecycle debris.",
        start_time=now - timedelta(days=45, hours=2),
        end_time=now - timedelta(days=45),
        status=status,
        created_by=seller,
    )


def create_lot(*, auction, status=LotStatus.OPEN):
    return Lot.objects.create(
        auction=auction,
        title="QA Lot",
        description="Temporary QA lot.",
        starting_price=Decimal("50.00"),
        current_price=Decimal("50.00"),
        bid_increment=Decimal("5.00"),
        status=status,
    )


def test_staging_reset_qa_data_command_exists():
    assert "staging_reset_qa_data" in get_commands()
    assert "seed_staging_qa_baseline" in get_commands()


def test_staging_reset_qa_data_dry_run_writes_nothing(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("dry_reset_seller", role=UserRole.SELLER)
    auction = create_qa_auction(seller=seller)
    lot = create_lot(auction=auction)
    before = data_snapshot()
    output = StringIO()

    call_command("staging_reset_qa_data", stdout=output)

    assert "mode=dry-run" in output.getvalue()
    assert "No data was modified." in output.getvalue()
    assert f"auction_id={auction.id}" in output.getvalue()
    assert Lot.objects.filter(pk=lot.id).exists()
    assert data_snapshot() == before


def test_staging_reset_qa_data_apply_refuses_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "bidals-backend")
    seller = create_user("prod_guard_seller", role=UserRole.SELLER)
    auction = create_qa_auction(seller=seller)

    with pytest.raises(CommandError, match="allowed only"):
        call_command("staging_reset_qa_data", apply=True)

    assert Auction.objects.filter(pk=auction.id).exists()


def test_staging_reset_qa_data_preserves_admin_accounts(monkeypatch):
    allow_staging(monkeypatch)
    admin = create_user("reset_admin", role=UserRole.ADMIN, is_superuser=True)
    seller = create_user("admin_preserve_seller", role=UserRole.SELLER)
    create_qa_auction(seller=seller)

    call_command("staging_reset_qa_data", apply=True)

    admin.refresh_from_db()
    assert admin.is_superuser is True
    assert admin.is_staff is True
    assert User.objects.filter(pk=admin.id).exists()


def test_staging_reset_qa_data_preserves_protected_auctions(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("protected_seller", role=UserRole.SELLER)
    protected = create_qa_auction(seller=seller, title="[PROTECTED] QA- Keep This")
    removable = create_qa_auction(seller=seller, title="QA- Remove This")

    call_command("staging_reset_qa_data", apply=True)

    assert Auction.objects.filter(pk=protected.id).exists()
    assert not Auction.objects.filter(pk=removable.id).exists()


def test_staging_reset_qa_data_removes_qa_auction_graph_safely(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("remove_seller", role=UserRole.SELLER)
    bidder = create_user("remove_bidder")
    auction = create_qa_auction(seller=seller)
    lot = create_lot(auction=auction, status=LotStatus.SOLD)
    bid = Bid.objects.create(lot=lot, bidder=bidder, amount=Decimal("75.00"), status=BidStatus.ACCEPTED)
    lot.winner = bidder
    lot.winning_bid = bid
    lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
    lot.save(update_fields=("winner", "winning_bid", "winner_status", "updated_at"))
    fulfillment = FulfillmentRecord.objects.create(
        lot=lot,
        auction=auction,
        winning_bid=bid,
        winner=bidder,
        status=FulfillmentStatus.PENDING_CONFIRMATION,
    )
    notification = OutboundNotification.objects.create(
        recipient=bidder,
        recipient_email=bidder.email,
        notification_type="winner_assigned",
        subject="QA winner",
        body="QA cleanup notification.",
        related_entity_type="lot",
        related_entity_id=str(lot.id),
    )

    call_command("staging_reset_qa_data", apply=True)

    assert not Auction.objects.filter(pk=auction.id).exists()
    assert not Lot.objects.filter(pk=lot.id).exists()
    assert not Bid.objects.filter(pk=bid.id).exists()
    assert not FulfillmentRecord.objects.filter(pk=fulfillment.id).exists()
    assert not OutboundNotification.objects.filter(pk=notification.id).exists()
    assert User.objects.filter(pk=seller.id).exists()
    assert User.objects.filter(pk=bidder.id).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.ADMIN_ACTION,
        entity_type="staging_qa_reset",
        metadata__source="staging_reset_qa_data",
    ).exists()


def test_staging_reset_qa_data_repeated_apply_is_idempotent(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("idempotent_reset_seller", role=UserRole.SELLER)
    create_qa_auction(seller=seller)

    call_command("staging_reset_qa_data", apply=True)
    after_first = data_snapshot()
    call_command("staging_reset_qa_data", apply=True)

    assert data_snapshot() == after_first


def test_staging_reset_qa_data_readiness_related_counts_clean_after_reset(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("readiness_reset_seller", role=UserRole.SELLER)
    auction = create_qa_auction(seller=seller, title="Retest stale auction", status=AuctionStatus.LIVE)
    create_lot(auction=auction, status=LotStatus.OPEN)

    call_command("staging_reset_qa_data", apply=True)

    summary = reset_summary()
    assert summary["inconsistent_lots"] == 0
    assert summary["stale_effective_ended_auctions"] == 0
    assert summary["orphan_notifications"] == 0


def test_staging_reset_qa_data_json_output_is_valid(monkeypatch):
    allow_staging(monkeypatch)
    seller = create_user("json_reset_seller", role=UserRole.SELLER)
    create_qa_auction(seller=seller)
    output = StringIO()

    call_command("staging_reset_qa_data", json=True, stdout=output)

    payload = json.loads(output.getvalue())
    assert payload["mode"] == "dry-run"
    assert payload["planned"]["auctions"] == 1
    assert payload["candidates"][0]["reasons"]


def test_seed_staging_qa_baseline_creates_clean_baseline(monkeypatch):
    allow_staging(monkeypatch)
    output = StringIO()

    call_command("seed_staging_qa_baseline", stdout=output)

    auction = Auction.objects.get(title=QA_BASELINE_AUCTION_TITLE)
    assert auction.status == AuctionStatus.LIVE
    assert auction.lots.count() == 3
    assert User.objects.filter(username="qa_seller", role=UserRole.SELLER).exists()
    assert User.objects.filter(username="qa_bidder_one", role=UserRole.BIDDER).exists()
    assert reset_summary()["inconsistent_lots"] == 0
    assert "seed_staging_qa_baseline" in output.getvalue()


def data_snapshot():
    return {
        "users": list(User.objects.order_by("id").values("id", "username", "is_staff", "is_superuser")),
        "auctions": list(Auction.objects.order_by("id").values("id", "title", "status")),
        "lots": list(Lot.objects.order_by("id").values("id", "auction_id", "status")),
        "bids": list(Bid.objects.order_by("id").values("id", "lot_id", "amount", "status")),
        "fulfillment": list(FulfillmentRecord.objects.order_by("id").values("id", "lot_id", "status")),
        "notifications": list(
            OutboundNotification.objects.order_by("id").values("id", "related_entity_type", "related_entity_id")
        ),
        "audit_count": AuditLog.objects.count(),
    }
