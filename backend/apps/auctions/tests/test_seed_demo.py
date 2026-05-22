from io import StringIO

import pytest
from django.core.management import call_command

from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, Lot, LotStatus

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_premium_browse_event_with_local_images():
    output = StringIO()

    call_command("seed_demo", stdout=output)

    rendered = output.getvalue()
    assert "BIDALS demo data seeded" in rendered

    auction = Auction.objects.get(title="[Demo] BIDALS Premium Benefit Auction")
    assert auction.status == AuctionStatus.LIVE

    lots = list(Lot.objects.filter(auction=auction).order_by("id"))
    assert [lot.title for lot in lots] == [
        "[Demo] Starter Wine Cellar",
        "[Demo] Reserve Swiss Watch Set",
        "[Demo] Increment Travel Retreat",
    ]
    assert all(lot.status == LotStatus.OPEN for lot in lots)
    assert lots[0].images == [
        "/demo-lots/wine-hero.webp",
        "/demo-lots/wine-detail.webp",
        "/demo-lots/wine-lifestyle.webp",
    ]
    assert lots[1].images == [
        "/demo-lots/watch-hero.webp",
        "/demo-lots/watch-detail.webp",
        "/demo-lots/watch-box.webp",
    ]
    assert lots[2].images == [
        "/demo-lots/vacation-resort.webp",
        "/demo-lots/vacation-room.webp",
        "/demo-lots/vacation-spa.webp",
        "/demo-lots/vacation-dinner.webp",
    ]
    assert Bid.objects.filter(lot__in=lots, status=BidStatus.ACCEPTED).count() == 5


def test_seed_demo_is_idempotent_for_demo_seller_records():
    call_command("seed_demo", stdout=StringIO())
    first_counts = (
        Auction.objects.filter(title__startswith="[Demo]").count(),
        Lot.objects.filter(auction__title__startswith="[Demo]").count(),
        Bid.objects.filter(lot__auction__title__startswith="[Demo]").count(),
    )

    call_command("seed_demo", stdout=StringIO())

    assert (
        Auction.objects.filter(title__startswith="[Demo]").count(),
        Lot.objects.filter(auction__title__startswith="[Demo]").count(),
        Bid.objects.filter(lot__auction__title__startswith="[Demo]").count(),
    ) == first_counts
