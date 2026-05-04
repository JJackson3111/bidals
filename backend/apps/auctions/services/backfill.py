from dataclasses import dataclass
import logging

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import AuctionStatus, BidStatus, FulfillmentRecord, Lot, LotStatus, LotWinnerStatus
from apps.auctions.services.fulfillment import ensure_fulfillment_record_for_lot
from apps.auctions.services.notifications import emit_notification_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackfillWinnerOutcomeResult:
    lot_id: int
    auction_id: int
    action: str
    outcome_status: str | None = None
    winner_id: int | None = None
    winning_bid_id: int | None = None
    fulfillment_created: bool = False
    dry_run: bool = False
    skipped_reason: str | None = None


def backfill_winner_outcomes(
    *,
    dry_run: bool = False,
    auction_id: int | None = None,
    lot_id: int | None = None,
    now=None,
) -> list[BackfillWinnerOutcomeResult]:
    """Repair missing backend-owned winner outcomes without changing bid history."""
    now = now or timezone.now()
    lots = (
        Lot.objects.select_related("auction")
        .filter(auction__status=AuctionStatus.ENDED)
        .exclude(status=LotStatus.CANCELLED)
        .order_by("auction__end_time", "auction_id", "id")
    )
    if auction_id:
        lots = lots.filter(auction_id=auction_id)
    if lot_id:
        lots = lots.filter(id=lot_id)

    results = [_backfill_lot(lot_id=lot.id, dry_run=dry_run, now=now) for lot in lots]
    logger.info(
        "Winner outcome backfill completed",
        extra={
            "event": "winner_outcome_backfill_run",
            "dry_run": dry_run,
            "auction_id": auction_id,
            "lot_id": lot_id,
            "lots_seen": len(results),
            "repairs": sum(1 for result in results if result.action != "skipped"),
        },
    )
    return results


def _backfill_lot(*, lot_id: int, dry_run: bool, now) -> BackfillWinnerOutcomeResult:
    with transaction.atomic():
        lot = (
            Lot.objects.select_for_update(of=("self",))
            .select_related("auction")
            .get(pk=lot_id)
        )

        if lot.auction.status != AuctionStatus.ENDED:
            return _skipped(lot, "auction_not_ended", dry_run=dry_run)
        if lot.status == LotStatus.CANCELLED:
            return _skipped(lot, "lot_cancelled", dry_run=dry_run)

        outcome_missing = not lot.winner_calculated_at or lot.winner_status == LotWinnerStatus.PENDING
        fulfillment_missing = _fulfillment_missing(lot)

        if not outcome_missing and not fulfillment_missing:
            return _skipped(lot, "already_complete", dry_run=dry_run)

        outcome = _determine_outcome(lot)
        if dry_run:
            would_create_fulfillment = (
                outcome["winner_status"] == LotWinnerStatus.WINNER_ASSIGNED
                and not FulfillmentRecord.objects.filter(lot=lot).exists()
            )
            action = "would_backfill_outcome" if outcome_missing else "would_create_fulfillment"
            return BackfillWinnerOutcomeResult(
                lot_id=lot.id,
                auction_id=lot.auction_id,
                action=action,
                outcome_status=outcome["winner_status"],
                winner_id=outcome["winner_id"],
                winning_bid_id=outcome["winning_bid_id"],
                fulfillment_created=would_create_fulfillment,
                dry_run=True,
            )

        if outcome_missing:
            _apply_outcome(lot=lot, outcome=outcome, now=now)
            AuditLog.objects.create(
                actor=None,
                action=AuditAction.WINNER_OUTCOME_BACKFILLED,
                entity_type="lot",
                entity_id=str(lot.id),
                server_timestamp=now,
                metadata={
                    "source": "backfill_winner_outcomes",
                    "auction_id": lot.auction_id,
                    "lot_id": lot.id,
                    "winner_status": lot.winner_status,
                    "winner_id": lot.winner_id,
                    "winning_bid_id": lot.winning_bid_id,
                    "reserve_price": str(lot.reserve_price) if lot.reserve_price is not None else None,
                    **outcome["metadata"],
                },
            )
            logger.info(
                "Winner outcome backfilled",
                extra={
                    "event": "winner_outcome_backfilled",
                    "auction_id": lot.auction_id,
                    "lot_id": lot.id,
                    "winner_status": lot.winner_status,
                    "winner_id": lot.winner_id,
                    "winning_bid_id": lot.winning_bid_id,
                },
            )

        created_fulfillment = False
        if _fulfillment_missing(lot):
            ensure_fulfillment_record_for_lot(
                lot=lot,
                source="backfill_winner_outcomes",
                metadata_extra={"repair_reason": "missing_fulfillment_record"},
            )
            created_fulfillment = True

        if outcome_missing and lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED:
            emit_notification_event(
                event_type="winner_assigned",
                recipient=lot.winner,
                entity_type="lot",
                entity_id=str(lot.id),
                metadata={
                    "source": "backfill_winner_outcomes",
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "winning_bid_id": lot.winning_bid_id,
                    "amount": str(lot.winning_bid.amount),
                },
            )

        return BackfillWinnerOutcomeResult(
            lot_id=lot.id,
            auction_id=lot.auction_id,
            action="backfilled_outcome" if outcome_missing else "created_fulfillment",
            outcome_status=lot.winner_status,
            winner_id=lot.winner_id,
            winning_bid_id=lot.winning_bid_id,
            fulfillment_created=created_fulfillment,
            dry_run=False,
        )


def _determine_outcome(lot: Lot) -> dict:
    highest_bid = (
        lot.bids.filter(status=BidStatus.ACCEPTED)
        .select_related("bidder")
        .order_by("-amount", "server_timestamp", "id")
        .first()
    )
    if highest_bid is None:
        return {
            "lot_status": LotStatus.CLOSED,
            "winner": None,
            "winner_id": None,
            "winning_bid": None,
            "winning_bid_id": None,
            "winner_status": LotWinnerStatus.NO_BIDS,
            "metadata": {},
        }

    metadata = {
        "highest_bid_id": highest_bid.id,
        "highest_bidder_id": highest_bid.bidder_id,
        "highest_amount": str(highest_bid.amount),
    }
    if lot.reserve_price is not None and highest_bid.amount < lot.reserve_price:
        return {
            "lot_status": LotStatus.CLOSED,
            "winner": None,
            "winner_id": None,
            "winning_bid": None,
            "winning_bid_id": None,
            "winner_status": LotWinnerStatus.RESERVE_NOT_MET,
            "metadata": metadata,
        }

    return {
        "lot_status": LotStatus.SOLD,
        "winner": highest_bid.bidder,
        "winner_id": highest_bid.bidder_id,
        "winning_bid": highest_bid,
        "winning_bid_id": highest_bid.id,
        "winner_status": LotWinnerStatus.WINNER_ASSIGNED,
        "metadata": {
            "winning_bid_id": highest_bid.id,
            "winner_id": highest_bid.bidder_id,
            "winning_amount": str(highest_bid.amount),
        },
    }


def _apply_outcome(*, lot: Lot, outcome: dict, now) -> None:
    lot.status = outcome["lot_status"]
    lot.winner = outcome["winner"]
    lot.winning_bid = outcome["winning_bid"]
    lot.winner_status = outcome["winner_status"]
    lot.winner_calculated_at = now
    lot.save(
        update_fields=(
            "status",
            "winner",
            "winning_bid",
            "winner_status",
            "winner_calculated_at",
            "updated_at",
        )
    )


def _fulfillment_missing(lot: Lot) -> bool:
    return (
        lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
        and lot.winner_id is not None
        and lot.winning_bid_id is not None
        and not FulfillmentRecord.objects.filter(lot=lot).exists()
    )


def _skipped(lot: Lot, reason: str, *, dry_run: bool) -> BackfillWinnerOutcomeResult:
    return BackfillWinnerOutcomeResult(
        lot_id=lot.id,
        auction_id=lot.auction_id,
        action="skipped",
        outcome_status=lot.winner_status,
        winner_id=lot.winner_id,
        winning_bid_id=lot.winning_bid_id,
        dry_run=dry_run,
        skipped_reason=reason,
    )
