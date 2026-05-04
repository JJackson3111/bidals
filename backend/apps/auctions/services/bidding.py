from dataclasses import dataclass
from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import (
    Bid,
    BidRejectionReason,
    BidStatus,
    Lot,
    LotStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BidResult:
    status: str
    lot_id: int
    current_price: Decimal
    server_timestamp: object
    bid_id: int | None = None
    reason: str | None = None

    @property
    def accepted(self) -> bool:
        return self.status == BidStatus.ACCEPTED

    def as_dict(self) -> dict:
        data = {
            "status": self.status,
            "lot_id": self.lot_id,
            "current_price": self.current_price,
            "server_timestamp": self.server_timestamp,
        }
        if self.bid_id is not None:
            data["bid_id"] = self.bid_id
        if self.reason:
            data["reason"] = self.reason
        return data


def place_bid(user, lot_id: int, amount: Decimal) -> BidResult:
    amount = Decimal(amount)

    with transaction.atomic():
        # The lot row is the bid-critical state. Lock it before reading price/status
        # so concurrent bids validate against the latest committed server state.
        lot = (
            Lot.objects.select_for_update()
            .select_related("auction", "auction__created_by")
            .get(pk=lot_id)
        )
        auction = lot.auction
        server_timestamp = timezone.now()

        if not user or not user.is_authenticated:
            return _reject_bid(
                actor=None,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.UNAUTHENTICATED,
                server_timestamp=server_timestamp,
                create_bid_record=False,
            )

        if not _user_can_bid(user, lot):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.USER_NOT_ALLOWED,
                server_timestamp=server_timestamp,
            )

        if not auction.is_live_at(server_timestamp):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.AUCTION_NOT_LIVE,
                server_timestamp=server_timestamp,
            )

        if lot.status != LotStatus.OPEN:
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.LOT_CLOSED,
                server_timestamp=server_timestamp,
            )

        previous_price = lot.current_price
        if amount <= previous_price:
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.BID_TOO_LOW,
                server_timestamp=server_timestamp,
            )

        if not _is_valid_increment(amount=amount, current_price=previous_price, increment=lot.bid_increment):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.INVALID_INCREMENT,
                server_timestamp=server_timestamp,
            )

        bid = Bid.objects.create(
            lot=lot,
            bidder=user,
            amount=amount,
            status=BidStatus.ACCEPTED,
            server_timestamp=server_timestamp,
        )
        lot.current_price = amount
        lot.save(update_fields=("current_price", "updated_at"))

        AuditLog.objects.create(
            actor=user,
            action=AuditAction.BID_ACCEPTED,
            entity_type="bid",
            entity_id=str(bid.id),
            server_timestamp=server_timestamp,
            metadata={
                "lot_id": lot.id,
                "auction_id": auction.id,
                "bidder_id": user.id,
                "amount": str(amount),
                "previous_price": str(previous_price),
                "new_price": str(lot.current_price),
            },
        )
        logger.info(
            "Bid accepted",
            extra={
                "event": "bid_accepted",
                "lot_id": lot.id,
                "auction_id": auction.id,
                "bidder_id": user.id,
                "amount": str(amount),
                "previous_price": str(previous_price),
                "new_price": str(lot.current_price),
                "server_timestamp": server_timestamp.isoformat(),
            },
        )

        return BidResult(
            status=BidStatus.ACCEPTED,
            lot_id=lot.id,
            bid_id=bid.id,
            current_price=lot.current_price,
            server_timestamp=server_timestamp,
        )


def _reject_bid(
    *,
    actor,
    lot: Lot,
    amount: Decimal,
    reason: str,
    server_timestamp,
    create_bid_record: bool = True,
) -> BidResult:
    bid = None
    if create_bid_record:
        bid = Bid.objects.create(
            lot=lot,
            bidder=actor,
            amount=amount,
            status=BidStatus.REJECTED,
            rejection_reason=reason,
            server_timestamp=server_timestamp,
        )

    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.BID_REJECTED,
        entity_type="bid" if bid else "lot",
        entity_id=str(bid.id if bid else lot.id),
        server_timestamp=server_timestamp,
        metadata={
            "lot_id": lot.id,
            "auction_id": lot.auction_id,
            "bidder_id": actor.id if actor else None,
            "attempted_amount": str(amount),
            "current_price": str(lot.current_price),
            "reason": reason,
        },
    )
    logger.warning(
        "Bid rejected",
        extra={
            "event": "bid_rejected",
            "lot_id": lot.id,
            "auction_id": lot.auction_id,
            "bidder_id": actor.id if actor else None,
            "attempted_amount": str(amount),
            "current_price": str(lot.current_price),
            "rejection_reason": reason,
            "server_timestamp": server_timestamp.isoformat(),
        },
    )

    return BidResult(
        status=BidStatus.REJECTED,
        lot_id=lot.id,
        bid_id=bid.id if bid else None,
        current_price=lot.current_price,
        server_timestamp=server_timestamp,
        reason=reason,
    )


def _user_can_bid(user, lot: Lot) -> bool:
    if user.is_platform_admin:
        return True

    if user.role not in {UserRole.BIDDER, UserRole.SELLER}:
        return False

    return lot.auction.created_by_id != user.id


def _is_valid_increment(*, amount: Decimal, current_price: Decimal, increment: Decimal) -> bool:
    delta = amount - current_price
    if delta < increment:
        return False

    return delta % increment == Decimal("0.00")
