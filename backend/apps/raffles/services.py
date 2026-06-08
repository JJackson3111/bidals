from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import secrets

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction
from apps.raffles.models import (
    RaffleCampaign,
    RaffleCampaignStatus,
    RaffleDraw,
    RafflePrize,
    RafflePurchase,
    RafflePurchaseStatus,
    RaffleTicket,
    RaffleTicketStatus,
    RaffleWinner,
    SellerRaffleFeature,
)


class RaffleError(Exception):
    pass


class RafflePermissionError(RaffleError):
    pass


class RaffleFeatureDisabledError(RaffleError):
    pass


@dataclass(frozen=True)
class RafflePurchaseResult:
    purchase: RafflePurchase
    tickets: list[RaffleTicket]

    def as_dict(self) -> dict:
        return {
            "purchase_id": self.purchase.id,
            "campaign_id": self.purchase.campaign_id,
            "buyer_id": self.purchase.buyer_id,
            "quantity": self.purchase.quantity,
            "ticket_ids": [ticket.id for ticket in self.tickets],
            "ticket_numbers": [ticket.ticket_number for ticket in self.tickets],
        }


@dataclass(frozen=True)
class RaffleWinnerResult:
    winner: RaffleWinner

    def as_dict(self) -> dict:
        return {
            "winner_id": self.winner.id,
            "campaign_id": self.winner.campaign_id,
            "prize_id": self.winner.prize_id,
            "ticket_id": self.winner.ticket_id,
            "ticket_number": self.winner.ticket.ticket_number,
            "user_id": self.winner.winner_id,
        }


@dataclass(frozen=True)
class RaffleDrawResult:
    draw: RaffleDraw
    winners: list[RaffleWinner]

    def as_dict(self) -> dict:
        return {
            "draw_id": self.draw.id,
            "campaign_id": self.draw.campaign_id,
            "drawn_at": self.draw.drawn_at,
            "winners": [RaffleWinnerResult(winner).as_dict() for winner in self.winners],
        }


def seller_has_raffles_enabled(seller) -> bool:
    if not seller:
        return False
    feature = getattr(seller, "raffle_feature", None)
    if feature is None:
        try:
            feature = SellerRaffleFeature.objects.get(seller=seller)
        except SellerRaffleFeature.DoesNotExist:
            return False
    return feature.has_raffles


def ensure_raffles_enabled_for_seller(seller) -> None:
    if not seller_has_raffles_enabled(seller):
        raise RaffleFeatureDisabledError("Raffles are not enabled for this seller.")


def create_campaign(*, actor, data: dict) -> RaffleCampaign:
    if not _is_seller_or_admin(actor):
        raise RafflePermissionError("Only sellers and admins can create raffles.")

    campaign_data = dict(data)
    auction = campaign_data.get("auction")
    if auction is not None:
        auction = _coerce_auction(auction)
        if not actor.is_platform_admin and auction.created_by_id != actor.id:
            raise RafflePermissionError("You can only create raffles for your own auctions.")
        owner = auction.created_by
        campaign_data["auction"] = auction
    else:
        owner = actor

    ensure_raffles_enabled_for_seller(owner)
    campaign_data["created_by"] = owner

    campaign = RaffleCampaign(**campaign_data)
    campaign.full_clean()
    campaign.save()

    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.RAFFLE_CAMPAIGN_CREATED,
        entity_type="raffle_campaign",
        entity_id=str(campaign.id),
        metadata={
            "raffle_campaign_id": campaign.id,
            "auction_id": campaign.auction_id,
            "actor_id": actor.id if actor else None,
            "created_by_id": campaign.created_by_id,
            "title": campaign.title,
            "status": campaign.status,
            "ticket_price": str(campaign.ticket_price),
            "max_tickets": campaign.max_tickets,
        },
    )
    return campaign


def update_campaign(*, actor, campaign_id: int, data: dict) -> RaffleCampaign:
    with transaction.atomic():
        campaign = (
            RaffleCampaign.objects.select_for_update(of=("self",))
            .select_related("auction", "created_by")
            .get(pk=campaign_id)
        )
        _ensure_can_manage_campaign(actor=actor, campaign=campaign)
        if not actor.is_platform_admin:
            ensure_raffles_enabled_for_seller(campaign.created_by)

        if campaign.status in {RaffleCampaignStatus.DRAWN, RaffleCampaignStatus.CANCELLED}:
            raise RaffleError("Drawn and cancelled raffles cannot be edited.")

        update_data = dict(data)
        if "auction" in update_data and update_data["auction"] is not None:
            update_data["auction"] = _coerce_auction(update_data["auction"])
            if not actor.is_platform_admin and update_data["auction"].created_by_id != actor.id:
                raise RafflePermissionError("You can only link raffles to your own auctions.")

        new_status = update_data.get("status", campaign.status)
        _validate_status_transition(current=campaign.status, new=new_status, source="campaign_update")

        protected_fields = {"auction", "ticket_price", "max_tickets", "start_time", "end_time", "draw_time"}
        if protected_fields.intersection(update_data) and _campaign_has_tickets(campaign):
            raise RaffleError("Ticketed raffles cannot change auction, price, capacity, or timing fields.")

        previous_status = campaign.status
        previous_values = {
            "title": campaign.title,
            "description": campaign.description,
            "ticket_price": str(campaign.ticket_price),
            "start_time": campaign.start_time.isoformat(),
            "end_time": campaign.end_time.isoformat(),
            "draw_time": campaign.draw_time.isoformat(),
            "max_tickets": campaign.max_tickets,
            "status": campaign.status,
            "auction_id": campaign.auction_id,
        }

        for field, value in update_data.items():
            if field in {"created_by", "created_by_id"}:
                continue
            setattr(campaign, field, value)

        campaign.full_clean()
        campaign.save()

        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_CAMPAIGN_UPDATED,
            entity_type="raffle_campaign",
            entity_id=str(campaign.id),
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "updated_fields": sorted(update_data.keys()),
                "previous_status": previous_status,
                "new_status": campaign.status,
                "previous_state": previous_values,
                "new_state": {
                    "title": campaign.title,
                    "description": campaign.description,
                    "ticket_price": str(campaign.ticket_price),
                    "start_time": campaign.start_time.isoformat(),
                    "end_time": campaign.end_time.isoformat(),
                    "draw_time": campaign.draw_time.isoformat(),
                    "max_tickets": campaign.max_tickets,
                    "status": campaign.status,
                    "auction_id": campaign.auction_id,
                },
            },
        )
        if campaign.status == RaffleCampaignStatus.CANCELLED and previous_status != campaign.status:
            _audit_campaign_cancelled(actor=actor, campaign=campaign, previous_status=previous_status)
    return campaign


def create_prize(*, actor, campaign_id: int, data: dict) -> RafflePrize:
    with transaction.atomic():
        campaign = RaffleCampaign.objects.select_for_update().select_related("created_by").get(pk=campaign_id)
        _ensure_can_manage_campaign(actor=actor, campaign=campaign)
        if campaign.status not in {RaffleCampaignStatus.DRAFT, RaffleCampaignStatus.SCHEDULED}:
            raise RaffleError("Prizes can only be added before a raffle is live.")

        prize = RafflePrize(campaign=campaign, **data)
        prize.full_clean()
        prize.save()
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_PRIZE_CREATED,
            entity_type="raffle_prize",
            entity_id=str(prize.id),
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "prize_id": prize.id,
                "position": prize.position,
                "title": prize.title,
            },
        )
    return prize


def complete_purchase_and_issue_tickets(
    *,
    actor,
    campaign_id: int,
    buyer,
    quantity: int,
    gross_amount: Decimal | None = None,
    platform_fee_amount: Decimal = Decimal("0.00"),
    charity_amount: Decimal | None = None,
    payment_reference: str = "",
    request_context: dict | None = None,
) -> RafflePurchaseResult:
    request_context = request_context or {}
    quantity = int(quantity)
    if quantity <= 0:
        raise RaffleError("Ticket quantity must be positive.")
    _ensure_buyer_can_purchase(buyer=buyer)

    with transaction.atomic():
        campaign = (
            RaffleCampaign.objects.select_for_update(of=("self",))
            .select_related("auction", "created_by")
            .get(pk=campaign_id)
        )
        ensure_raffles_enabled_for_seller(campaign.created_by)
        _ensure_campaign_can_sell_tickets(campaign=campaign, buyer=buyer)

        issued_ticket_rows = list(
            RaffleTicket.objects.select_for_update()
            .filter(campaign=campaign)
            .order_by("ticket_number", "id")
        )
        active_ticket_count = sum(1 for ticket in issued_ticket_rows if ticket.status == RaffleTicketStatus.ACTIVE)
        if active_ticket_count + quantity > campaign.max_tickets:
            raise RaffleError("This purchase would exceed the raffle ticket capacity.")

        last_ticket_number = (
            RaffleTicket.objects.filter(campaign=campaign).aggregate(max_number=Max("ticket_number"))["max_number"]
            or 0
        )
        first_ticket_number = last_ticket_number + 1
        ticket_numbers = list(range(first_ticket_number, first_ticket_number + quantity))

        gross_amount = _money(gross_amount if gross_amount is not None else campaign.ticket_price * quantity)
        platform_fee_amount = _money(platform_fee_amount)
        charity_amount = _money(charity_amount if charity_amount is not None else gross_amount - platform_fee_amount)
        if gross_amount != platform_fee_amount + charity_amount:
            raise RaffleError("Gross amount must equal platform fee plus charity amount.")
        if min(gross_amount, platform_fee_amount, charity_amount) < Decimal("0.00"):
            raise RaffleError("Purchase amounts cannot be negative.")

        purchase = RafflePurchase(
            campaign=campaign,
            buyer=buyer,
            quantity=quantity,
            gross_amount=gross_amount,
            platform_fee_amount=platform_fee_amount,
            charity_amount=charity_amount,
            payment_reference=(payment_reference or "").strip(),
            status=RafflePurchaseStatus.COMPLETED,
        )
        purchase.full_clean()
        purchase.save()

        tickets = [
            RaffleTicket.objects.create(
                campaign=campaign,
                purchase=purchase,
                owner=buyer,
                ticket_number=ticket_number,
                status=RaffleTicketStatus.ACTIVE,
            )
            for ticket_number in ticket_numbers
        ]

        ticket_metadata = _ticket_metadata(ticket_numbers)
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_PURCHASE_COMPLETED,
            entity_type="raffle_purchase",
            entity_id=str(purchase.id),
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "buyer_id": buyer.id,
                "purchase_id": purchase.id,
                "ticket_quantity": quantity,
                "gross_amount": str(gross_amount),
                "platform_fee_amount": str(platform_fee_amount),
                "charity_amount": str(charity_amount),
                "payment_reference_present": bool(purchase.payment_reference),
                **request_context,
            },
        )
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_TICKETS_ISSUED,
            entity_type="raffle_purchase",
            entity_id=str(purchase.id),
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "buyer_id": buyer.id,
                "purchase_id": purchase.id,
                "ticket_quantity": quantity,
                **ticket_metadata,
                **request_context,
            },
        )

    return RafflePurchaseResult(purchase=purchase, tickets=tickets)


def close_raffle(*, actor, campaign_id: int, comment: str = "") -> RaffleCampaign:
    with transaction.atomic():
        campaign = RaffleCampaign.objects.select_for_update().select_related("created_by").get(pk=campaign_id)
        _ensure_can_manage_campaign(actor=actor, campaign=campaign)
        if campaign.status == RaffleCampaignStatus.CLOSED:
            return campaign
        _validate_status_transition(current=campaign.status, new=RaffleCampaignStatus.CLOSED, source="close_raffle")

        previous_status = campaign.status
        campaign.status = RaffleCampaignStatus.CLOSED
        campaign.save(update_fields=("status", "updated_at"))
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_CLOSED,
            entity_type="raffle_campaign",
            entity_id=str(campaign.id),
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "previous_status": previous_status,
                "new_status": campaign.status,
                "comment_present": bool((comment or "").strip()),
            },
        )
    return campaign


def execute_draw(*, actor, campaign_id: int) -> RaffleDrawResult:
    with transaction.atomic():
        campaign = (
            RaffleCampaign.objects.select_for_update(of=("self",))
            .select_related("created_by", "auction")
            .get(pk=campaign_id)
        )
        _ensure_can_manage_campaign(actor=actor, campaign=campaign)

        if campaign.status != RaffleCampaignStatus.CLOSED:
            raise RaffleError("Raffle must be closed before it can be drawn.")
        if RaffleDraw.objects.filter(campaign=campaign).exists():
            raise RaffleError("This raffle has already been drawn.")

        tickets = list(
            RaffleTicket.objects.select_for_update()
            .select_related("owner")
            .filter(campaign=campaign, status=RaffleTicketStatus.ACTIVE)
            .order_by("ticket_number", "id")
        )
        if not tickets:
            raise RaffleError("Raffle cannot be drawn with zero active tickets.")

        prizes = list(
            RafflePrize.objects.select_for_update()
            .filter(campaign=campaign)
            .order_by("position", "id")
        )
        if not prizes:
            raise RaffleError("Raffle cannot be drawn without prizes.")
        if len(prizes) > len(tickets):
            raise RaffleError("Raffle has more prizes than active tickets; one ticket cannot win multiple prizes.")

        pool = list(tickets)
        nonce = secrets.token_hex(32)
        selections = []
        for prize in prizes:
            selected_index = secrets.randbelow(len(pool))
            ticket = pool.pop(selected_index)
            selections.append(
                {
                    "prize": prize,
                    "ticket": ticket,
                    "selected_index": selected_index,
                    "pool_size_before_selection": len(pool) + 1,
                }
            )

        drawn_at = timezone.now()
        randomness_metadata = {
            "algorithm": "secrets.randbelow_without_replacement",
            "randomness_source": "python.secrets.SystemRandom",
            "nonce": nonce,
            "ticket_pool_size": len(tickets),
            "prize_count": len(prizes),
            "one_ticket_can_win_multiple_prizes": False,
            "selections": [
                {
                    "prize_id": item["prize"].id,
                    "prize_position": item["prize"].position,
                    "ticket_id": item["ticket"].id,
                    "ticket_number": item["ticket"].ticket_number,
                    "selected_index": item["selected_index"],
                    "pool_size_before_selection": item["pool_size_before_selection"],
                }
                for item in selections
            ],
        }
        draw = RaffleDraw.objects.create(
            campaign=campaign,
            drawn_by=actor,
            drawn_at=drawn_at,
            randomness_metadata=randomness_metadata,
        )

        winners = []
        for item in selections:
            ticket = item["ticket"]
            prize = item["prize"]
            winners.append(
                RaffleWinner.objects.create(
                    campaign=campaign,
                    prize=prize,
                    ticket=ticket,
                    winner=ticket.owner,
                )
            )

        previous_status = campaign.status
        campaign.status = RaffleCampaignStatus.DRAWN
        campaign.save(update_fields=("status", "updated_at"))

        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.RAFFLE_DRAW_EXECUTED,
            entity_type="raffle_draw",
            entity_id=str(draw.id),
            server_timestamp=drawn_at,
            metadata={
                "raffle_campaign_id": campaign.id,
                "auction_id": campaign.auction_id,
                "actor_id": actor.id if actor else None,
                "draw_id": draw.id,
                "previous_status": previous_status,
                "new_status": campaign.status,
                "ticket_pool_size": len(tickets),
                "prize_count": len(prizes),
                "winning_ticket_ids": [winner.ticket_id for winner in winners],
                "winning_ticket_numbers": [winner.ticket.ticket_number for winner in winners],
                "one_ticket_can_win_multiple_prizes": False,
            },
        )
        for winner in winners:
            AuditLog.objects.create(
                actor=actor,
                action=AuditAction.RAFFLE_WINNER_ASSIGNED,
                entity_type="raffle_winner",
                entity_id=str(winner.id),
                server_timestamp=drawn_at,
                metadata={
                    "raffle_campaign_id": campaign.id,
                    "auction_id": campaign.auction_id,
                    "actor_id": actor.id if actor else None,
                    "draw_id": draw.id,
                    "winner_id": winner.winner_id,
                    "prize_id": winner.prize_id,
                    "winning_ticket_id": winner.ticket_id,
                    "winning_ticket_number": winner.ticket.ticket_number,
                },
            )

    return RaffleDrawResult(draw=draw, winners=winners)


def read_user_tickets(*, user, campaign_id: int | None = None):
    tickets = (
        RaffleTicket.objects.select_related("campaign", "purchase", "owner")
        .filter(owner=user)
        .order_by("-issued_at", "-id")
    )
    if campaign_id is not None:
        tickets = tickets.filter(campaign_id=campaign_id)
    return tickets


def read_winners(*, campaign_id: int):
    return (
        RaffleWinner.objects.select_related("campaign", "prize", "ticket", "winner")
        .filter(campaign_id=campaign_id)
        .order_by("prize__position", "id")
    )


def _coerce_auction(auction) -> Auction:
    if isinstance(auction, Auction):
        return auction
    return Auction.objects.select_related("created_by").get(pk=auction)


def _is_seller_or_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.can_sell)


def _ensure_can_manage_campaign(*, actor, campaign: RaffleCampaign) -> None:
    if not _is_seller_or_admin(actor):
        raise RafflePermissionError("Only sellers and admins can manage raffles.")
    if actor.is_platform_admin:
        return
    if campaign.created_by_id != actor.id:
        raise RafflePermissionError("You can only manage your own raffles.")


def _ensure_buyer_can_purchase(*, buyer) -> None:
    if not buyer or not buyer.is_authenticated:
        raise RafflePermissionError("You must be authenticated to buy raffle tickets.")
    if buyer.is_platform_admin:
        raise RafflePermissionError("Admins cannot buy raffle tickets.")
    if buyer.role not in {UserRole.BIDDER, UserRole.SELLER}:
        raise RafflePermissionError("This account cannot buy raffle tickets.")


def _ensure_campaign_can_sell_tickets(*, campaign: RaffleCampaign, buyer) -> None:
    now = timezone.now()
    if campaign.status != RaffleCampaignStatus.LIVE:
        raise RaffleError("Raffle tickets can only be issued while the raffle is live.")
    if not campaign.is_live_at(now):
        raise RaffleError("Raffle tickets can only be issued inside the raffle sales window.")
    if campaign.created_by_id == buyer.id:
        raise RafflePermissionError("Sellers cannot buy tickets for their own raffle.")
    if campaign.auction_id and campaign.auction.created_by_id == buyer.id:
        raise RafflePermissionError("Sellers cannot buy tickets for their own event.")


def _campaign_has_tickets(campaign: RaffleCampaign) -> bool:
    return RaffleTicket.objects.filter(campaign=campaign).exists()


def _validate_status_transition(*, current: str, new: str, source: str) -> None:
    allowed = {
        RaffleCampaignStatus.DRAFT: {
            RaffleCampaignStatus.DRAFT,
            RaffleCampaignStatus.SCHEDULED,
            RaffleCampaignStatus.LIVE,
            RaffleCampaignStatus.CANCELLED,
        },
        RaffleCampaignStatus.SCHEDULED: {
            RaffleCampaignStatus.SCHEDULED,
            RaffleCampaignStatus.DRAFT,
            RaffleCampaignStatus.LIVE,
            RaffleCampaignStatus.CLOSED,
            RaffleCampaignStatus.CANCELLED,
        },
        RaffleCampaignStatus.LIVE: {
            RaffleCampaignStatus.LIVE,
            RaffleCampaignStatus.CLOSED,
            RaffleCampaignStatus.CANCELLED,
        },
        RaffleCampaignStatus.CLOSED: {
            RaffleCampaignStatus.CLOSED,
            RaffleCampaignStatus.CANCELLED,
            RaffleCampaignStatus.DRAWN,
        },
        RaffleCampaignStatus.DRAWN: {RaffleCampaignStatus.DRAWN},
        RaffleCampaignStatus.CANCELLED: {RaffleCampaignStatus.CANCELLED},
    }
    if new == RaffleCampaignStatus.DRAWN and source != "execute_draw":
        raise RaffleError("Raffle draw status is controlled by the draw engine.")
    if new == RaffleCampaignStatus.CLOSED and source == "campaign_update":
        raise RaffleError("Use the close raffle workflow to close a raffle.")
    if new not in allowed.get(current, {current}):
        raise RaffleError(f"Raffle status cannot transition from {current} to {new}.")


def _audit_campaign_cancelled(*, actor, campaign: RaffleCampaign, previous_status: str) -> None:
    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.RAFFLE_CANCELLED,
        entity_type="raffle_campaign",
        entity_id=str(campaign.id),
        metadata={
            "raffle_campaign_id": campaign.id,
            "auction_id": campaign.auction_id,
            "actor_id": actor.id if actor else None,
            "previous_status": previous_status,
            "new_status": campaign.status,
        },
    )


def _ticket_metadata(ticket_numbers: list[int]) -> dict:
    if not ticket_numbers:
        return {"ticket_numbers": [], "ticket_number_range": None}
    return {
        "ticket_numbers": ticket_numbers if len(ticket_numbers) <= 100 else ticket_numbers[:100],
        "ticket_numbers_truncated": len(ticket_numbers) > 100,
        "ticket_number_range": {
            "first": min(ticket_numbers),
            "last": max(ticket_numbers),
        },
    }


def _money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
