from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus
from apps.raffles.models import (
    RaffleCampaign,
    RaffleCampaignStatus,
    RaffleDraw,
    RafflePlanCode,
    RafflePrize,
    RafflePurchase,
    RafflePurchaseStatus,
    RaffleTicket,
    RaffleTicketStatus,
    RaffleWinner,
    SellerRaffleFeature,
)
from apps.raffles.services import (
    RaffleError,
    RaffleFeatureDisabledError,
    RafflePermissionError,
    close_raffle,
    complete_purchase_and_issue_tickets,
    create_campaign,
    create_prize,
    execute_draw,
)

pytestmark = pytest.mark.django_db(transaction=True)

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def enable_raffles(seller, *, plan=RafflePlanCode.SIGNATURE, enabled=False):
    return SellerRaffleFeature.objects.create(
        seller=seller,
        plan_code=plan,
        raffles_enabled=enabled,
    )


def create_auction(*, seller, status=AuctionStatus.LIVE):
    now = timezone.now()
    return Auction.objects.create(
        title=f"{seller.username} auction",
        description="Auction for raffle tests.",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        status=status,
        created_by=seller,
    )


def campaign_payload(*, auction=None, status=RaffleCampaignStatus.LIVE, title="Raffle"):
    now = timezone.now()
    return {
        "auction": auction,
        "title": title,
        "description": "A production-grade raffle test.",
        "ticket_price": Decimal("5.00"),
        "start_time": now - timedelta(minutes=5),
        "end_time": now + timedelta(minutes=30),
        "draw_time": now + timedelta(minutes=45),
        "max_tickets": 100,
        "status": status,
    }


def create_enabled_campaign(*, seller=None, status=RaffleCampaignStatus.LIVE, title="Raffle"):
    seller = seller or create_user("seller", role=UserRole.SELLER)
    enable_raffles(seller)
    auction = create_auction(seller=seller)
    return create_campaign(
        actor=seller,
        data=campaign_payload(auction=auction, status=status, title=title),
    )


def add_prizes(campaign, count=1):
    return [
        RafflePrize.objects.create(
            campaign=campaign,
            title=f"Prize {position}",
            description="Prize description.",
            position=position,
        )
        for position in range(1, count + 1)
    ]


def issue_tickets(campaign, buyer, quantity=1, *, actor=None):
    return complete_purchase_and_issue_tickets(
        actor=actor or campaign.created_by,
        campaign_id=campaign.id,
        buyer=buyer,
        quantity=quantity,
    )


def test_feature_flag_disabled_blocks_seller_raffle_creation():
    seller = create_user("seller", role=UserRole.SELLER)
    auction = create_auction(seller=seller)

    with pytest.raises(RaffleFeatureDisabledError):
        create_campaign(actor=seller, data=campaign_payload(auction=auction))

    assert RaffleCampaign.objects.count() == 0


def test_signature_plan_allows_raffle_creation_and_audits():
    seller = create_user("seller", role=UserRole.SELLER)
    enable_raffles(seller, plan=RafflePlanCode.SIGNATURE)
    auction = create_auction(seller=seller)

    campaign = create_campaign(actor=seller, data=campaign_payload(auction=auction))

    assert campaign.created_by == seller
    assert campaign.auction == auction
    assert AuditLog.objects.filter(
        action=AuditAction.RAFFLE_CAMPAIGN_CREATED,
        metadata__raffle_campaign_id=campaign.id,
        metadata__auction_id=auction.id,
    ).exists()


def test_essentials_add_on_allows_raffle_creation():
    seller = create_user("seller", role=UserRole.SELLER)
    enable_raffles(seller, plan=RafflePlanCode.ESSENTIALS, enabled=True)
    auction = create_auction(seller=seller)

    campaign = create_campaign(actor=seller, data=campaign_payload(auction=auction))

    assert campaign.id is not None


def test_disabled_feature_hides_bidder_facing_campaign_but_admin_can_read():
    seller = create_user("seller", role=UserRole.SELLER)
    admin = create_user("admin", role=UserRole.ADMIN)
    campaign = RaffleCampaign.objects.create(
        created_by=seller,
        **campaign_payload(status=RaffleCampaignStatus.LIVE),
    )
    bidder_client = APIClient()
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin)

    bidder_response = bidder_client.get("/api/raffles/")
    admin_response = admin_client.get(f"/api/raffles/{campaign.id}/")

    assert bidder_response.status_code == 200
    assert campaign.id not in [item["id"] for item in bidder_response.data["results"]]
    assert admin_response.status_code == 200
    assert admin_response.data["id"] == campaign.id


def test_create_prize_audits_privileged_action():
    seller = create_user("seller", role=UserRole.SELLER)
    campaign = create_enabled_campaign(seller=seller, status=RaffleCampaignStatus.SCHEDULED)

    prize = create_prize(
        actor=seller,
        campaign_id=campaign.id,
        data={"title": "First prize", "description": "Signed item.", "position": 1},
    )

    assert prize.campaign == campaign
    assert AuditLog.objects.filter(
        action=AuditAction.RAFFLE_PRIZE_CREATED,
        metadata__raffle_campaign_id=campaign.id,
        metadata__prize_id=prize.id,
    ).exists()


def test_purchase_completion_issues_correct_quantity_and_unique_ticket_numbers():
    campaign = create_enabled_campaign()
    first_buyer = create_user("first_buyer")
    second_buyer = create_user("second_buyer")

    first = issue_tickets(campaign, first_buyer, quantity=3)
    second = issue_tickets(campaign, second_buyer, quantity=2)

    assert first.purchase.status == RafflePurchaseStatus.COMPLETED
    assert [ticket.ticket_number for ticket in first.tickets] == [1, 2, 3]
    assert [ticket.ticket_number for ticket in second.tickets] == [4, 5]
    assert set(
        RaffleTicket.objects.filter(campaign=campaign).values_list("ticket_number", flat=True)
    ) == {1, 2, 3, 4, 5}
    assert AuditLog.objects.filter(action=AuditAction.RAFFLE_PURCHASE_COMPLETED).count() == 2
    assert AuditLog.objects.filter(action=AuditAction.RAFFLE_TICKETS_ISSUED).count() == 2


def test_ticket_numbers_are_unique_per_campaign():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    result = issue_tickets(campaign, buyer, quantity=1)
    purchase = result.purchase

    with pytest.raises(IntegrityError):
        RaffleTicket.objects.create(
            campaign=campaign,
            purchase=purchase,
            owner=buyer,
            ticket_number=result.tickets[0].ticket_number,
            status=RaffleTicketStatus.ACTIVE,
        )


def test_ticket_immutability_blocks_reassignment_after_issue():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    ticket = issue_tickets(campaign, buyer, quantity=1).tickets[0]

    ticket.ticket_number = 99
    with pytest.raises(ValidationError):
        ticket.save()

    other_buyer = create_user("other_buyer")
    ticket.refresh_from_db()
    ticket.owner = other_buyer
    with pytest.raises(ValidationError):
        ticket.save()


def test_only_completed_purchases_can_issue_active_tickets():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    purchase = RafflePurchase.objects.create(
        campaign=campaign,
        buyer=buyer,
        quantity=1,
        gross_amount=Decimal("5.00"),
        platform_fee_amount=Decimal("0.00"),
        charity_amount=Decimal("5.00"),
        status=RafflePurchaseStatus.PENDING,
    )

    with pytest.raises(ValidationError):
        RaffleTicket.objects.create(
            campaign=campaign,
            purchase=purchase,
            owner=buyer,
            ticket_number=1,
            status=RaffleTicketStatus.ACTIVE,
        )


def test_seller_cannot_buy_tickets_for_own_raffle():
    seller = create_user("seller", role=UserRole.SELLER)
    campaign = create_enabled_campaign(seller=seller)

    with pytest.raises(RafflePermissionError):
        issue_tickets(campaign, seller, quantity=1)


def test_admin_cannot_buy_raffle_tickets():
    campaign = create_enabled_campaign()
    admin = create_user("admin", role=UserRole.ADMIN)

    with pytest.raises(RafflePermissionError):
        issue_tickets(campaign, admin, quantity=1)


def test_buyers_can_view_only_their_own_tickets():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    other_buyer = create_user("other_buyer")
    issue_tickets(campaign, buyer, quantity=2)
    issue_tickets(campaign, other_buyer, quantity=1)
    client = APIClient()
    client.force_authenticate(user=buyer)

    response = client.get("/api/raffle-tickets/mine/")

    assert response.status_code == 200
    assert [ticket["ticket_number"] for ticket in response.data["results"]] == [2, 1]
    assert {ticket["owner"] for ticket in response.data["results"]} == {buyer.id}


def test_raffle_cannot_draw_before_closed_state():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    add_prizes(campaign, count=1)
    issue_tickets(campaign, buyer, quantity=1)

    with pytest.raises(RaffleError):
        execute_draw(actor=campaign.created_by, campaign_id=campaign.id)


def test_raffle_cannot_draw_with_zero_active_tickets():
    campaign = create_enabled_campaign()
    add_prizes(campaign, count=1)
    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)

    with pytest.raises(RaffleError):
        execute_draw(actor=campaign.created_by, campaign_id=campaign.id)


def test_draw_creates_winners_and_correct_relationships():
    campaign = create_enabled_campaign()
    first_buyer = create_user("first_buyer")
    second_buyer = create_user("second_buyer")
    add_prizes(campaign, count=2)
    issue_tickets(campaign, first_buyer, quantity=1)
    issue_tickets(campaign, second_buyer, quantity=1)
    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)

    result = execute_draw(actor=campaign.created_by, campaign_id=campaign.id)

    campaign.refresh_from_db()
    assert campaign.status == RaffleCampaignStatus.DRAWN
    assert result.draw.campaign == campaign
    assert RaffleWinner.objects.filter(campaign=campaign).count() == 2
    assert len({winner.prize_id for winner in result.winners}) == 2
    assert len({winner.ticket_id for winner in result.winners}) == 2
    for winner in result.winners:
        assert winner.ticket.campaign_id == campaign.id
        assert winner.prize.campaign_id == campaign.id
        assert winner.winner_id == winner.ticket.owner_id
    assert result.draw.randomness_metadata["one_ticket_can_win_multiple_prizes"] is False


def test_duplicate_draw_is_prevented():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    add_prizes(campaign, count=1)
    issue_tickets(campaign, buyer, quantity=1)
    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)

    execute_draw(actor=campaign.created_by, campaign_id=campaign.id)

    with pytest.raises(RaffleError):
        execute_draw(actor=campaign.created_by, campaign_id=campaign.id)

    assert RaffleDraw.objects.filter(campaign=campaign).count() == 1


def test_draw_rolls_back_winners_and_status_when_audit_fails():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    add_prizes(campaign, count=1)
    issue_tickets(campaign, buyer, quantity=1)
    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)

    with patch("apps.raffles.services.AuditLog.objects.create", side_effect=RuntimeError("audit unavailable")):
        with pytest.raises(RuntimeError):
            execute_draw(actor=campaign.created_by, campaign_id=campaign.id)

    campaign.refresh_from_db()
    assert campaign.status == RaffleCampaignStatus.CLOSED
    assert RaffleDraw.objects.filter(campaign=campaign).count() == 0
    assert RaffleWinner.objects.filter(campaign=campaign).count() == 0


def test_winners_are_immutable_after_draw():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    add_prizes(campaign, count=1)
    issue_tickets(campaign, buyer, quantity=1)
    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)
    winner = execute_draw(actor=campaign.created_by, campaign_id=campaign.id).winners[0]

    other_user = create_user("other_user")
    winner.winner = other_user
    with pytest.raises(ValidationError):
        winner.save()


def test_audit_logs_are_created_for_close_draw_and_winner_assignment():
    campaign = create_enabled_campaign()
    buyer = create_user("buyer")
    add_prizes(campaign, count=1)
    issue_tickets(campaign, buyer, quantity=1)

    close_raffle(actor=campaign.created_by, campaign_id=campaign.id)
    result = execute_draw(actor=campaign.created_by, campaign_id=campaign.id)

    assert AuditLog.objects.filter(
        action=AuditAction.RAFFLE_CLOSED,
        metadata__raffle_campaign_id=campaign.id,
    ).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.RAFFLE_DRAW_EXECUTED,
        metadata__draw_id=result.draw.id,
    ).exists()
    assert AuditLog.objects.filter(
        action=AuditAction.RAFFLE_WINNER_ASSIGNED,
        metadata__winning_ticket_id=result.winners[0].ticket_id,
    ).exists()
