from datetime import timedelta
from decimal import Decimal
from io import StringIO
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command, get_commands
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditLog
from apps.audit.services.staging_diagnostics import mask_url, url_fingerprint
from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, FulfillmentRecord, Lot, LotStatus

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def test_deployment_fingerprint_command_exists():
    assert "deployment_fingerprint" in get_commands()


def test_staging_lifecycle_issue_details_command_exists():
    assert "staging_lifecycle_issue_details" in get_commands()


def test_deployment_fingerprint_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://db_user:db-secret@postgres.internal:5432/bidals")
    monkeypatch.setenv("REDIS_URL", "redis://redis_user:redis-secret@redis.internal:6379/0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "django-secret-value")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890abcdef1234567890abcdef12")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "tighten-seller-browse-isolation")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "bidals-backend-staging")
    output = StringIO()

    call_command("deployment_fingerprint", stdout=output)

    rendered = output.getvalue()
    assert "deployment_fingerprint" in rendered
    assert "git_commit_sha=abcdef1234567890abcdef1234567890abcdef12" in rendered
    assert "git_branch=tighten-seller-browse-isolation" in rendered
    assert "render_service_name=bidals-backend-staging" in rendered
    assert "file_staging_env_diagnostics.py=True" in rendered
    assert "file_staging_lifecycle_readiness.py=True" in rendered
    assert "deployment_fingerprint" in rendered
    assert "staging_env_diagnostics" in rendered
    assert "staging_lifecycle_readiness" in rendered
    assert "DATABASE_URL" not in rendered
    assert "REDIS_URL" not in rendered
    assert "SECRET_KEY" not in rendered
    assert "db_user" not in rendered
    assert "db-secret" not in rendered
    assert "redis_user" not in rendered
    assert "redis-secret" not in rendered
    assert "django-secret-value" not in rendered


@pytest.mark.django_db
def test_staging_lifecycle_issue_details_is_read_only_and_outputs_flagged_records():
    seller = create_user("issue_seller", role=UserRole.SELLER)
    winner = create_user("issue_winner")
    auction = create_live_auction(seller=seller)
    closed_lot = create_lot(auction=auction, title="Closed Inside Live", status=LotStatus.CLOSED)
    open_lot = create_lot(auction=auction, title="Open With Winner", status=LotStatus.OPEN, winner=winner)
    Bid.objects.create(
        lot=closed_lot,
        bidder=winner,
        amount=Decimal("125.00"),
        status=BidStatus.ACCEPTED,
        server_timestamp=timezone.now(),
    )
    before = readonly_snapshot()
    output = StringIO()

    call_command("staging_lifecycle_issue_details", stdout=output)

    rendered = output.getvalue()
    assert "staging_lifecycle_issue_details" in rendered
    assert "closed_lot_inside_live_auction" in rendered
    assert "open_lot_has_outcome_data" in rendered
    assert f"auction_id={auction.id}" in rendered
    assert f"lot_id={closed_lot.id}" in rendered
    assert f"lot_id={open_lot.id}" in rendered
    assert "Closed Inside Live" in rendered
    assert "Open With Winner" in rendered
    assert "winner_email=i***@example.com" in rendered
    assert "issue_winner@example.com" not in rendered
    assert readonly_snapshot() == before


@pytest.mark.django_db
def test_staging_lifecycle_issue_details_json_outputs_flagged_records():
    seller = create_user("json_issue_seller", role=UserRole.SELLER)
    winner = create_user("json_issue_winner")
    auction = create_live_auction(seller=seller)
    create_lot(auction=auction, title="JSON Closed", status=LotStatus.CLOSED)
    open_lot = create_lot(auction=auction, title="JSON Winner", status=LotStatus.OPEN, winner=winner)
    output = StringIO()

    call_command("staging_lifecycle_issue_details", json=True, stdout=output)

    payload = json.loads(output.getvalue())
    assert payload["errors"] == []
    assert payload["summary"]["inconsistent_lots"] == 2
    assert payload["summary"]["closed_lots_in_live_auctions"] == 1
    assert payload["summary"]["live_lots_in_closed_auctions"] == 0
    assert len(payload["lot_issues"]) == 2
    issue_by_lot = {issue["lot_id"]: issue for issue in payload["lot_issues"]}
    assert "open_lot_has_outcome_data" in issue_by_lot[open_lot.id]["reasons"]
    assert issue_by_lot[open_lot.id]["winner_email"] == "j***@example.com"
    assert "json_issue_winner@example.com" not in output.getvalue()


def test_mask_url_hides_credentials_and_query_values():
    postgres_url = "postgres://db_user:db-pass@postgres.internal:5432/bidals?sslmode=require"
    redis_url = "redis://:redis-token@redis.internal:6379/0"

    masked_postgres = mask_url(postgres_url)
    masked_redis = mask_url(redis_url)
    fingerprint = url_fingerprint(postgres_url)

    assert masked_postgres == "postgres://***:***@postgres.internal:5432/bidals?query=present"
    assert masked_redis == "redis://:***@redis.internal:6379/0"
    assert fingerprint.startswith("sha256:")
    assert "db_user" not in masked_postgres
    assert "db-pass" not in masked_postgres
    assert "sslmode=require" not in masked_postgres
    assert "redis-token" not in masked_redis
    assert "db-pass" not in fingerprint


@override_settings(
    REDIS_URL="redis://diagnostic_user:redis-secret-token@redis.internal:6379/0",
    USE_REDIS_CACHE=True,
)
def test_staging_env_diagnostics_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://db_user:db-secret@postgres.internal:5432/bidals")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "django-secret-value")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    output = StringIO()

    with patch(
        "apps.audit.services.staging_diagnostics.redis_connection_status",
        return_value=("PASS", "ping succeeded"),
    ):
        call_command("staging_env_diagnostics", stdout=output)

    rendered = output.getvalue()
    assert "redis://***:***@redis.internal:6379/0" in rendered
    assert "redis_connection=PASS (ping succeeded)" in rendered
    assert "abcdef1234567890" in rendered
    assert "diagnostic_user" not in rendered
    assert "redis-secret-token" not in rendered
    assert "db_user" not in rendered
    assert "db-secret" not in rendered
    assert "django-secret-value" not in rendered
    assert "DATABASE_URL" not in rendered
    assert "SECRET_KEY" not in rendered


@override_settings(USE_TZ=False, TIME_ZONE="Europe/London")
@pytest.mark.django_db
def test_staging_lifecycle_readiness_reports_failures_safely(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://bad_user:bad-token@redis.internal:6379/0")
    output = StringIO()

    with (
        patch("apps.audit.services.staging_diagnostics.database_timezone", return_value=("Europe/London", None)),
        patch("apps.audit.services.staging_diagnostics.get_applied_migrations", return_value=set()),
    ):
        call_command("staging_lifecycle_readiness", stdout=output)

    rendered = output.getvalue()
    assert "[FAIL] USE_TZ: USE_TZ must be True." in rendered
    assert "[FAIL] TIME_ZONE: TIME_ZONE must be UTC." in rendered
    assert "[FAIL] DATABASE_TIMEZONE: timezone=Europe/London; expected UTC" in rendered
    assert "[FAIL] AUCTIONS_MIGRATION_0009" in rendered
    assert "[FAIL] AUDIT_MIGRATION_0011" in rendered
    assert "summary:" in rendered
    assert "bad_user" not in rendered
    assert "bad-token" not in rendered


def create_live_auction(*, seller):
    now = timezone.now()
    return Auction.objects.create(
        title="Lifecycle Issue Auction",
        description="A live auction used for read-only issue detail tests.",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
        status=AuctionStatus.LIVE,
        created_by=seller,
    )


def create_lot(*, auction, title, status, winner=None):
    return Lot.objects.create(
        auction=auction,
        title=title,
        description="A lot intentionally shaped for issue detail tests.",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        bid_increment=Decimal("5.00"),
        status=status,
        winner=winner,
    )


def readonly_snapshot():
    return {
        "auctions": list(
            Auction.objects.order_by("id").values("id", "status", "start_time", "end_time", "updated_at")
        ),
        "lots": list(
            Lot.objects.order_by("id").values(
                "id",
                "auction_id",
                "status",
                "current_price",
                "winner_id",
                "winning_bid_id",
                "winner_status",
                "winner_calculated_at",
                "updated_at",
            )
        ),
        "bids": list(Bid.objects.order_by("id").values("id", "lot_id", "bidder_id", "amount", "status")),
        "fulfillment_count": FulfillmentRecord.objects.count(),
        "audit_count": AuditLog.objects.count(),
    }
