from dataclasses import dataclass
from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidRejectionReason,
    BidStatus,
    Lot,
    LotStatus,
)
from apps.auctions.services.lifecycle import (
    get_effective_auction_status,
    get_effective_lot_status,
    is_lot_biddable,
    sync_locked_auction_status,
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


def place_bid(user, lot_id: int, amount: Decimal, request_context: dict | None = None) -> BidResult:
    amount = Decimal(amount)
    request_context = request_context or {}
    lot_snapshot = Lot.objects.only("id", "auction_id").get(pk=lot_id)

    with transaction.atomic():
        # Lock auction before lot so bid submission and lifecycle jobs take rows in
        # the same order. The eligibility checks below use this locked state.
        auction = Auction.objects.select_for_update().select_related("created_by").get(pk=lot_snapshot.auction_id)
        lot = (
            Lot.objects.select_for_update()
            .select_related("auction", "auction__created_by")
            .get(pk=lot_id)
        )
        if lot.auction_id != auction.id:
            auction = Auction.objects.select_for_update().select_related("created_by").get(pk=lot.auction_id)
        lot.auction = auction
        server_timestamp = timezone.now()
        effective_auction_status, _ = sync_locked_auction_status(
            auction,
            now=server_timestamp,
            source="bid_submission",
        )
        effective_lot_status = get_effective_lot_status(lot, now=server_timestamp)

        if not user or not user.is_authenticated:
            return _reject_bid(
                actor=None,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.UNAUTHENTICATED,
                server_timestamp=server_timestamp,
                create_bid_record=False,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
            )

        if not _user_can_bid(user, lot):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.USER_NOT_ALLOWED,
                server_timestamp=server_timestamp,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
            )

        if effective_auction_status != AuctionStatus.LIVE:
            reason = (
                BidRejectionReason.AUCTION_ENDED
                if effective_auction_status == AuctionStatus.ENDED
                else BidRejectionReason.AUCTION_NOT_STARTED
            )
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=reason,
                server_timestamp=server_timestamp,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
            )

        if effective_lot_status != LotStatus.OPEN or not is_lot_biddable(lot, now=server_timestamp):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.LOT_CLOSED,
                server_timestamp=server_timestamp,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
            )

        previous_price = lot.current_price
        if amount <= previous_price:
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.BID_TOO_LOW,
                server_timestamp=server_timestamp,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
            )

        if not _is_valid_increment(amount=amount, current_price=previous_price, increment=lot.bid_increment):
            return _reject_bid(
                actor=user,
                lot=lot,
                amount=amount,
                reason=BidRejectionReason.INVALID_INCREMENT,
                server_timestamp=server_timestamp,
                effective_auction_status=effective_auction_status,
                effective_lot_status=effective_lot_status,
                request_context=request_context,
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
                "actor": "user",
                "previous_state": {
                    "auction_status": auction.status,
                    "lot_status": lot.status,
                    "current_price": str(previous_price),
                },
                "new_state": {
                    "auction_status": get_effective_auction_status(auction, now=server_timestamp),
                    "lot_status": get_effective_lot_status(lot, now=server_timestamp),
                    "current_price": str(lot.current_price),
                },
                "effective_auction_status": effective_auction_status,
                "effective_lot_status": effective_lot_status,
                **request_context,
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
    effective_auction_status: str | None = None,
    effective_lot_status: str | None = None,
    request_context: dict | None = None,
) -> BidResult:
    request_context = request_context or {}
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
            "actor": "user" if actor else "anonymous",
            "previous_state": {
                "auction_status": lot.auction.status,
                "lot_status": lot.status,
                "current_price": str(lot.current_price),
            },
            "new_state": {
                "auction_status": effective_auction_status or lot.auction.status,
                "lot_status": effective_lot_status or lot.status,
                "current_price": str(lot.current_price),
            },
            "effective_auction_status": effective_auction_status,
            "effective_lot_status": effective_lot_status,
            **request_context,
        },
    )
    AuditLog.objects.create(
        actor=actor,
        action=_bid_rejection_audit_action(reason),
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
            "actor": "user" if actor else "anonymous",
            "previous_state": {
                "auction_status": lot.auction.status,
                "lot_status": lot.status,
                "current_price": str(lot.current_price),
            },
            "new_state": {
                "auction_status": effective_auction_status or lot.auction.status,
                "lot_status": effective_lot_status or lot.status,
                "current_price": str(lot.current_price),
            },
            "effective_auction_status": effective_auction_status,
            "effective_lot_status": effective_lot_status,
            **request_context,
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


def _bid_rejection_audit_action(reason: str) -> str:
    if reason in {BidRejectionReason.UNAUTHENTICATED, BidRejectionReason.USER_NOT_ALLOWED, BidRejectionReason.SERVER_ERROR}:
        return AuditAction.BID_REJECTED_SECURITY
    return AuditAction.BID_REJECTED_VALIDATION


def _is_valid_increment(*, amount: Decimal, current_price: Decimal, increment: Decimal) -> bool:
    delta = amount - current_price
    if delta < increment:
        return False

    return delta % increment == Decimal("0.00")
