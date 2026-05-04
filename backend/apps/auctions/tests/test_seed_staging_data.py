from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.auctions.management.commands.seed_staging_data import STAGING_PREFIX
from apps.auctions.models import Auction, Bid, BidStatus, FulfillmentRecord, Lot

pytestmark = pytest.mark.django_db


def test_seed_staging_data_creates_labeled_operational_records(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")
    output = StringIO()

    call_command("seed_staging_data", stdout=output)

    rendered = output.getvalue()
    assert "BIDALS staging data seeded" in rendered
    assert "admin@bidals.staging.test" in rendered
    assert Auction.objects.filter(title__startswith=STAGING_PREFIX).count() == 3
    assert Lot.objects.filter(title__startswith="[DEMO LOT]").count() == 4
    assert Bid.objects.filter(status=BidStatus.ACCEPTED).exists()
    assert Bid.objects.filter(status=BidStatus.REJECTED).exists()
    assert FulfillmentRecord.objects.filter(public_winner_message__icontains="Staging-only").exists()
    assert OutboundNotification.objects.filter(metadata__staging_seed=True).exists()
    assert AuditLog.objects.filter(action=AuditAction.STAGING_SEED_RUN, metadata__staging_seed=True).exists()


def test_seed_staging_data_is_idempotent_for_staging_records(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "staging")

    call_command("seed_staging_data", stdout=StringIO())
    first_counts = (
        Auction.objects.filter(title__startswith=STAGING_PREFIX).count(),
        Lot.objects.filter(title__startswith="[DEMO LOT]").count(),
        FulfillmentRecord.objects.count(),
        OutboundNotification.objects.filter(metadata__staging_seed=True).count(),
    )
    call_command("seed_staging_data", stdout=StringIO())

    assert (
        Auction.objects.filter(title__startswith=STAGING_PREFIX).count(),
        Lot.objects.filter(title__startswith="[DEMO LOT]").count(),
        FulfillmentRecord.objects.count(),
        OutboundNotification.objects.filter(metadata__staging_seed=True).count(),
    ) == first_counts


def test_seed_staging_data_refuses_production_without_force(monkeypatch):
    monkeypatch.setenv("BIDALS_ENV", "production")

    with pytest.raises(CommandError):
        call_command("seed_staging_data", stdout=StringIO())

    assert Auction.objects.filter(title__startswith=STAGING_PREFIX).count() == 0
