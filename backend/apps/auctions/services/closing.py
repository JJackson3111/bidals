from dataclasses import dataclass, field
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.audit.services.alerts import send_alert
from apps.auctions.models import Auction, AuctionStatus, BidStatus, Lot, LotStatus, LotWinnerStatus
from apps.auctions.services.fulfillment import ensure_fulfillment_record_for_lot
from apps.auctions.services.notifications import emit_notification_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LotWinnerResult:
    lot_id: int
    result: str
    winning_bid_id: int | None = None
    winner_id: int | None = None
    amount: str | None = None
    skipped: bool = False


@dataclass(frozen=True)
class AuctionCloseResult:
    auction_id: int
    title: str
    status: str
    transitioned: bool
    lots_processed: int = 0
    winners: list[LotWinnerResult] = field(default_factory=list)
    skipped_reason: str | None = None


def close_expired_auctions(*, now=None, limit: int | None = None) -> list[AuctionCloseResult]:
    now = now or timezone.now()
    finalizable_lot_statuses = (LotStatus.DRAFT, LotStatus.OPEN, LotStatus.CLOSED, LotStatus.SOLD)
    candidates = (
        Auction.objects.filter(
            Q(status=AuctionStatus.LIVE, end_time__lte=now)
            | Q(
                status=AuctionStatus.ENDED,
                lots__winner_calculated_at__isnull=True,
                lots__status__in=finalizable_lot_statuses,
            )
        )
        .distinct()
        .order_by("end_time", "id")
    )
    if limit:
        candidates = candidates[:limit]

    results = []
    for auction in candidates:
        try:
            results.append(close_expired_auction(auction.id, now=now))
        except Exception as exc:
            _record_job_failure(
                job_name="close_expired_auctions",
                entity_type="auction",
                entity_id=str(auction.id),
                error=exc,
            )
            send_alert(
                event_type="auction_closing_job_failed",
                severity="critical",
                message="Auction closing job failed.",
                metadata={"auction_id": auction.id, "error_type": type(exc).__name__},
            )
            raise

    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_CLOSE_RUN,
        entity_type="job",
        entity_id="close_expired_auctions",
        server_timestamp=now,
        metadata={
            "job_name": "close_expired_auctions",
            "auctions_seen": len(results),
            "auctions_transitioned": sum(1 for result in results if result.transitioned),
            "lots_processed": sum(result.lots_processed for result in results),
        },
    )
    logger.info(
        "Auction close run completed",
        extra={
            "event": "auction_close_run",
            "auctions_seen": len(results),
            "auctions_transitioned": sum(1 for result in results if result.transitioned),
            "lots_processed": sum(result.lots_processed for result in results),
            "server_timestamp": now.isoformat(),
        },
    )
    return results


def close_expired_auction(auction_id: int, *, now=None) -> AuctionCloseResult:
    now = now or timezone.now()

    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction_id)
        if auction.status not in {AuctionStatus.LIVE, AuctionStatus.ENDED}:
            return AuctionCloseResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="auction_not_live_or_ended",
            )

        if auction.status == AuctionStatus.LIVE and auction.end_time > now:
            return AuctionCloseResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="auction_not_expired",
            )

        transitioned = False
        if auction.status == AuctionStatus.LIVE:
            auction.status = AuctionStatus.ENDED
            auction.save(update_fields=("status", "updated_at"))
            transitioned = True
            AuditLog.objects.create(
                actor=None,
                action=AuditAction.AUCTION_ENDED,
                entity_type="auction",
                entity_id=str(auction.id),
                server_timestamp=now,
                metadata={
                    "auction_id": auction.id,
                    "previous_status": AuctionStatus.LIVE,
                    "new_status": AuctionStatus.ENDED,
                    "end_time": auction.end_time.isoformat(),
                    "closed_by": "close_expired_auctions",
                },
            )
            logger.info(
                "Auction ended",
                extra={
                    "event": "auction_ended",
                    "auction_id": auction.id,
                    "previous_status": AuctionStatus.LIVE,
                    "new_status": AuctionStatus.ENDED,
                    "server_timestamp": now.isoformat(),
                },
            )

        lots = list(
            Lot.objects.select_for_update()
            .filter(auction=auction)
            .exclude(status=LotStatus.CANCELLED)
            .order_by("id")
        )
        winner_results = [_calculate_lot_winner(lot=lot, now=now) for lot in lots]

    lots_processed = sum(1 for result in winner_results if not result.skipped)
    if transitioned:
        emit_notification_event(
            event_type="auction_ended",
            recipient=auction.created_by,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={
                "auction_id": auction.id,
                "lots_processed": lots_processed,
            },
        )

    return AuctionCloseResult(
        auction_id=auction.id,
        title=auction.title,
        status=auction.status,
        transitioned=transitioned,
        lots_processed=lots_processed,
        winners=winner_results,
    )


def _calculate_lot_winner(*, lot: Lot, now) -> LotWinnerResult:
    if lot.winner_calculated_at:
        return LotWinnerResult(
            lot_id=lot.id,
            result=lot.winner_status,
            winning_bid_id=lot.winning_bid_id,
            winner_id=lot.winner_id,
            amount=str(lot.winning_bid.amount) if lot.winning_bid else None,
            skipped=True,
        )

    highest_bid = (
        lot.bids.filter(status=BidStatus.ACCEPTED)
        .select_related("bidder")
        .order_by("-amount", "server_timestamp", "id")
        .first()
    )

    previous_status = lot.status
    metadata = {
        "lot_id": lot.id,
        "auction_id": lot.auction_id,
        "previous_status": previous_status,
        "reserve_price": str(lot.reserve_price) if lot.reserve_price is not None else None,
    }

    if highest_bid is None:
        lot.status = LotStatus.CLOSED
        lot.winner = None
        lot.winning_bid = None
        lot.winner_status = LotWinnerStatus.NO_BIDS
        result = LotWinnerStatus.NO_BIDS
    elif lot.reserve_price is not None and highest_bid.amount < lot.reserve_price:
        lot.status = LotStatus.CLOSED
        lot.winner = None
        lot.winning_bid = None
        lot.winner_status = LotWinnerStatus.RESERVE_NOT_MET
        result = LotWinnerStatus.RESERVE_NOT_MET
        metadata.update(
            {
                "highest_bid_id": highest_bid.id,
                "highest_bidder_id": highest_bid.bidder_id,
                "highest_amount": str(highest_bid.amount),
            }
        )
    else:
        lot.status = LotStatus.SOLD
        lot.winner = highest_bid.bidder
        lot.winning_bid = highest_bid
        lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
        result = LotWinnerStatus.WINNER_ASSIGNED
        metadata.update(
            {
                "winning_bid_id": highest_bid.id,
                "winner_id": highest_bid.bidder_id,
                "winning_amount": str(highest_bid.amount),
            }
        )

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

    AuditLog.objects.create(
        actor=None,
        action=AuditAction.WINNER_CALCULATED,
        entity_type="lot",
        entity_id=str(lot.id),
        server_timestamp=now,
        metadata={
            **metadata,
            "new_status": lot.status,
            "winner_status": lot.winner_status,
        },
    )
    logger.info(
        "Winner calculated",
        extra={
            "event": "winner_calculated",
            "auction_id": lot.auction_id,
            "lot_id": lot.id,
            "winner_status": lot.winner_status,
            "winner_id": lot.winner_id,
            "winning_bid_id": lot.winning_bid_id,
            "server_timestamp": now.isoformat(),
        },
    )

    if lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED:
        ensure_fulfillment_record_for_lot(lot=lot)
        emit_notification_event(
            event_type="winner_assigned",
            recipient=lot.winner,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "lot_id": lot.id,
                "auction_id": lot.auction_id,
                "winning_bid_id": lot.winning_bid_id,
                "amount": str(lot.winning_bid.amount),
            },
        )

    return LotWinnerResult(
        lot_id=lot.id,
        result=result,
        winning_bid_id=lot.winning_bid_id,
        winner_id=lot.winner_id,
        amount=str(lot.winning_bid.amount) if lot.winning_bid else None,
    )


def _record_job_failure(*, job_name: str, entity_type: str, entity_id: str, error: Exception) -> None:
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.JOB_FAILED,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata={
            "job_name": job_name,
            "error_type": type(error).__name__,
        },
    )
    logger.exception(
        "Operational job failed",
        extra={
            "event": "job_failed",
            "job_name": job_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "error_type": type(error).__name__,
        },
    )
