from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.admin import AuctionAdmin, LotAdmin, LotInline, OutcomeRepairRequestAdmin
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidStatus,
    Lot,
    LotStatus,
    OutcomeRepairRequest,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER, *, is_staff=False, is_superuser=False):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


@pytest.fixture
def admin_user():
    return create_user("admin", role=UserRole.ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def admin_request(admin_user):
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    return request


def create_auction():
    seller = create_user("seller", role=UserRole.SELLER)
    now = timezone.now()
    return Auction.objects.create(
        title="Admin Safety Auction",
        description="A trust-sensitive admin test auction.",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(hours=1),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )


def create_lot():
    return Lot.objects.create(
        auction=create_auction(),
        title="Admin Safety Lot",
        description="A trust-sensitive admin test lot.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        reserve_price=Decimal("150.00"),
        bid_increment=Decimal("10.00"),
        status=LotStatus.OPEN,
    )


def test_auction_admin_lifecycle_fields_are_readonly_after_creation(admin_request):
    auction = create_auction()
    model_admin = AuctionAdmin(Auction, AdminSite())

    readonly_fields = set(model_admin.get_readonly_fields(admin_request, auction))

    assert {"status", "start_time", "end_time", "created_by"} <= readonly_fields
    assert model_admin.has_delete_permission(admin_request, auction) is False


def test_lot_admin_trust_sensitive_fields_are_readonly_after_creation(admin_request):
    lot = create_lot()
    model_admin = LotAdmin(Lot, AdminSite())
    inline_admin = LotInline(Auction, AdminSite())

    readonly_fields = set(model_admin.get_readonly_fields(admin_request, lot))
    inline_readonly_fields = set(inline_admin.get_readonly_fields(admin_request, lot.auction))

    assert {
        "auction",
        "status",
        "starting_price",
        "reserve_price",
        "bid_increment",
        "current_price",
        "winner",
        "winning_bid",
        "winner_status",
        "winner_calculated_at",
    } <= readonly_fields
    assert {"status", "starting_price", "bid_increment", "current_price", "winner_status"} <= inline_readonly_fields
    assert model_admin.has_delete_permission(admin_request, lot) is False


def test_auction_admin_allowed_edits_are_audited(admin_request):
    auction = create_auction()
    model_admin = AuctionAdmin(Auction, AdminSite())
    auction.title = "Admin Safety Auction Updated"

    model_admin.save_model(
        admin_request,
        auction,
        SimpleNamespace(changed_data=["title"]),
        change=True,
    )

    assert AuditLog.objects.filter(
        action=AuditAction.AUCTION_UPDATED,
        entity_type="auction",
        entity_id=str(auction.id),
        metadata__source="django_admin",
        metadata__changed_fields=["title"],
    ).exists()


def test_lot_admin_allowed_edits_are_audited(admin_request):
    lot = create_lot()
    model_admin = LotAdmin(Lot, AdminSite())
    lot.description = "Updated safely through Django admin."

    model_admin.save_model(
        admin_request,
        lot,
        SimpleNamespace(changed_data=["description"]),
        change=True,
    )

    assert AuditLog.objects.filter(
        action=AuditAction.LOT_UPDATED,
        entity_type="lot",
        entity_id=str(lot.id),
        metadata__source="django_admin",
        metadata__changed_fields=["description"],
    ).exists()


def test_outcome_repair_admin_is_view_only(admin_request):
    lot = create_lot()
    bidder = create_user("winning_bidder")
    bid = Bid.objects.create(lot=lot, bidder=bidder, amount=Decimal("150.00"), status=BidStatus.ACCEPTED)
    repair = OutcomeRepairRequest.objects.create(
        lot=lot,
        auction=lot.auction,
        current_outcome=lot.winner_status,
        requested_winning_bid=bid,
        requested_winner=bidder,
        requested_by=admin_request.user,
        reason="Admin view-only safety test.",
    )
    model_admin = OutcomeRepairRequestAdmin(OutcomeRepairRequest, AdminSite())

    readonly_fields = set(model_admin.get_readonly_fields(admin_request, repair))

    assert {
        "status",
        "requested_winning_bid",
        "requested_winner",
        "requested_by",
        "reviewed_by",
        "applied_by",
        "reviewed_at",
        "applied_at",
    } <= readonly_fields
    assert model_admin.has_add_permission(admin_request) is False
    assert model_admin.has_delete_permission(admin_request, repair) is False
