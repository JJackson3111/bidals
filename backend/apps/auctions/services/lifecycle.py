from dataclasses import dataclass, field
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.audit.services.alerts import send_alert
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    BidStatus,
    Lot,
    LotStatus,
    LotWinnerStatus,
)
from apps.auctions.services.fulfillment import ensure_fulfillment_record_for_lot
from apps.auctions.services.notifications import emit_notification_event

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = "system"
LEGACY_OPEN_AUCTION_STATUS = "open"
ACTIVE_AUCTION_STATUSES = (
    AuctionStatus.SCHEDULED,
    AuctionStatus.LIVE,
    LEGACY_OPEN_AUCTION_STATUS,
)
FINALIZABLE_AUCTION_STATUSES = (
    *ACTIVE_AUCTION_STATUSES,
    AuctionStatus.ENDED,
)


@dataclass(frozen=True)
class LotWinnerResult:
    lot_id: int
    result: str
    winning_bid_id: int | None = None
    winner_id: int | None = None
    amount: str | None = None
    skipped: bool = False
    skipped_reason: str | None = None


@dataclass(frozen=True)
class AuctionLifecycleResult:
    auction_id: int
    title: str
    status: str
    transitioned: bool
    lots_processed: int = 0
    winners: list[LotWinnerResult] = field(default_factory=list)
    skipped_reason: str | None = None


AuctionActivationResult = AuctionLifecycleResult
AuctionCloseResult = AuctionLifecycleResult


def current_lifecycle_time(now=None):
    """Return an aware backend timestamp for lifecycle decisions."""
    if now is None:
        return timezone.now()
    if timezone.is_naive(now):
        return timezone.make_aware(now, timezone.get_current_timezone())
    return now


def get_effective_auction_status(auction: Auction, now=None) -> str:
    now = current_lifecycle_time(now)
    if auction.status in {AuctionStatus.CANCELLED, AuctionStatus.DRAFT}:
        return auction.status
    if auction.status == AuctionStatus.ENDED:
        return AuctionStatus.ENDED
    if auction.end_time <= now:
        return AuctionStatus.ENDED
    if auction.start_time <= now < auction.end_time:
        return AuctionStatus.LIVE
    return AuctionStatus.SCHEDULED


def get_effective_lot_status(lot: Lot, now=None) -> str:
    now = current_lifecycle_time(now)
    if lot.status == LotStatus.CANCELLED:
        return LotStatus.CANCELLED
    if lot.status == LotStatus.SOLD or lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED:
        return LotStatus.SOLD
    if lot.status == LotStatus.CLOSED or lot.winner_status in {
        LotWinnerStatus.NO_BIDS,
        LotWinnerStatus.RESERVE_NOT_MET,
    }:
        return LotStatus.CLOSED
    if get_effective_auction_status(lot.auction, now=now) == AuctionStatus.ENDED:
        return LotStatus.CLOSED
    return lot.status


def get_lot_closure_reason(lot: Lot, now=None) -> str | None:
    now = current_lifecycle_time(now)
    if lot.status == LotStatus.CANCELLED:
        return "lot_cancelled"
    if lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED:
        return "sold"
    if lot.winner_status == LotWinnerStatus.NO_BIDS:
        return "no_bids"
    if lot.winner_status == LotWinnerStatus.RESERVE_NOT_MET:
        return "reserve_not_met"
    if lot.status == LotStatus.CLOSED:
        return "lot_closed"
    if get_effective_auction_status(lot.auction, now=now) == AuctionStatus.ENDED:
        return "auction_end_time_elapsed"
    return None


def get_auction_closure_reason(auction: Auction, now=None) -> str | None:
    now = current_lifecycle_time(now)
    if auction.status == AuctionStatus.CANCELLED:
        return "auction_cancelled"
    if auction.status == AuctionStatus.ENDED:
        return "auction_status_ended"
    if auction.end_time <= now:
        return "auction_end_time_elapsed"
    return None


def is_lot_biddable(lot: Lot, now=None) -> bool:
    now = current_lifecycle_time(now)
    return (
        get_effective_auction_status(lot.auction, now=now) == AuctionStatus.LIVE
        and lot.status == LotStatus.OPEN
        and get_effective_lot_status(lot, now=now) == LotStatus.OPEN
        and lot.winner_status == LotWinnerStatus.PENDING
        and lot.winner_calculated_at is None
    )


def sync_locked_auction_status(auction: Auction, *, now=None, source: str = "lifecycle") -> tuple[str, bool]:
    """Persist due scheduled/live status changes for an already locked auction row."""
    now = current_lifecycle_time(now)
    effective_status = get_effective_auction_status(auction, now=now)
    previous_status = auction.status

    if previous_status == effective_status:
        return effective_status, False

    if previous_status in ACTIVE_AUCTION_STATUSES and effective_status == AuctionStatus.LIVE:
        auction.status = AuctionStatus.LIVE
        auction.save(update_fields=("status", "updated_at"))
        _audit_auction_opened(auction=auction, previous_status=previous_status, now=now, source=source)
        return effective_status, True

    if previous_status in ACTIVE_AUCTION_STATUSES and effective_status == AuctionStatus.ENDED:
        auction.status = AuctionStatus.ENDED
        auction.save(update_fields=("status", "updated_at"))
        _audit_auction_closed(auction=auction, previous_status=previous_status, now=now, source=source)
        return effective_status, True

    return effective_status, False


def open_due_auctions(*, now=None, limit: int | None = None) -> list[AuctionLifecycleResult]:
    now = current_lifecycle_time(now)
    candidates = (
        Auction.objects.filter(
            status=AuctionStatus.SCHEDULED,
            start_time__lte=now,
            end_time__gt=now,
        )
        .order_by("start_time", "id")
        .values_list("id", flat=True)
    )
    if limit is not None:
        candidates = candidates[:limit]

    results = []
    errors = 0
    for auction_id in candidates:
        try:
            results.append(sync_auction_lifecycle(auction_id, now=now))
        except Exception as exc:
            errors += 1
            _record_job_failure(
                job_name="open_due_auctions",
                entity_type="auction",
                entity_id=str(auction_id),
                error=exc,
                now=now,
            )

    logger.info(
        "Due auction opening run completed",
        extra={
            "event": "open_due_auctions_run",
            "auctions_seen": len(results),
            "auctions_transitioned": sum(1 for result in results if result.transitioned),
            "errors": errors,
            "server_timestamp": now.isoformat(),
        },
    )
    _audit_lifecycle_noop(
        job_name="open_due_auctions",
        now=now,
        seen=len(results),
        transitioned=sum(1 for result in results if result.transitioned),
        errors=errors,
    )
    return results


def close_due_auctions(*, now=None, limit: int | None = None) -> list[AuctionLifecycleResult]:
    now = current_lifecycle_time(now)
    finalizable_lot_statuses = (LotStatus.DRAFT, LotStatus.OPEN, LotStatus.CLOSED, LotStatus.SOLD)
    candidates = (
        Auction.objects.filter(
            Q(status__in=ACTIVE_AUCTION_STATUSES, end_time__lte=now)
            | Q(
                status=AuctionStatus.ENDED,
                lots__winner_calculated_at__isnull=True,
                lots__status__in=finalizable_lot_statuses,
            )
            | Q(
                status=AuctionStatus.ENDED,
                lots__winner_status=LotWinnerStatus.WINNER_ASSIGNED,
                lots__fulfillment__isnull=True,
            )
        )
        .distinct()
        .order_by("end_time", "id")
        .values_list("id", flat=True)
    )
    if limit is not None:
        candidates = candidates[:limit]

    results = []
    errors = 0
    for auction_id in candidates:
        try:
            results.append(sync_auction_lifecycle(auction_id, now=now))
        except Exception as exc:
            errors += 1
            _record_job_failure(
                job_name="close_due_auctions",
                entity_type="auction",
                entity_id=str(auction_id),
                error=exc,
                now=now,
            )
            send_alert(
                event_type="auction_lifecycle_job_failed",
                severity="critical",
                message="Auction lifecycle close job failed for one auction.",
                metadata={"auction_id": auction_id, "error_type": type(exc).__name__},
            )

    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_CLOSE_RUN,
        entity_type="job",
        entity_id="close_due_auctions",
        server_timestamp=now,
        metadata={
            "actor": SYSTEM_ACTOR,
            "job_name": "close_due_auctions",
            "auctions_seen": len(results),
            "auctions_transitioned": sum(1 for result in results if result.transitioned),
            "lots_processed": sum(result.lots_processed for result in results),
            "errors": errors,
        },
    )
    logger.info(
        "Due auction closing run completed",
        extra={
            "event": "close_due_auctions_run",
            "auctions_seen": len(results),
            "auctions_transitioned": sum(1 for result in results if result.transitioned),
            "lots_processed": sum(result.lots_processed for result in results),
            "errors": errors,
            "server_timestamp": now.isoformat(),
        },
    )
    _audit_lifecycle_noop(
        job_name="close_due_auctions",
        now=now,
        seen=len(results),
        transitioned=sum(1 for result in results if result.transitioned),
        errors=errors,
    )
    return results


def close_due_lots(*, now=None, limit: int | None = None) -> list[LotWinnerResult]:
    now = current_lifecycle_time(now)
    candidates = (
        Lot.objects.select_related("auction")
        .filter(
            Q(auction__status=AuctionStatus.ENDED)
            | Q(auction__status__in=ACTIVE_AUCTION_STATUSES, auction__end_time__lte=now)
        )
        .exclude(status=LotStatus.CANCELLED)
        .order_by("auction__end_time", "auction_id", "id")
        .values_list("id", flat=True)
    )
    if limit is not None:
        candidates = candidates[:limit]

    results = []
    for lot_id in candidates:
        try:
            results.append(finalise_lot_outcome(lot_id, now=now))
        except Exception as exc:
            _record_job_failure(
                job_name="close_due_lots",
                entity_type="lot",
                entity_id=str(lot_id),
                error=exc,
                now=now,
            )
    return results


def finalise_lot_outcome(lot, now=None) -> LotWinnerResult:
    now = current_lifecycle_time(now)
    lot_id = lot.id if isinstance(lot, Lot) else lot
    with transaction.atomic():
        locked_lot = (
            Lot.objects.select_for_update(of=("self",))
            .select_related("auction", "winner", "winning_bid")
            .get(pk=lot_id)
        )
        return _finalise_locked_lot_outcome(lot=locked_lot, now=now)


def sync_auction_lifecycle(auction_id: int, now=None) -> AuctionLifecycleResult:
    now = current_lifecycle_time(now)
    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction_id)
        effective_status, transitioned = sync_locked_auction_status(
            auction,
            now=now,
            source="sync_auction_lifecycle",
        )

        if effective_status != AuctionStatus.ENDED:
            skipped_reason = _not_ended_skip_reason(auction=auction, effective_status=effective_status, now=now)
            return AuctionLifecycleResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=transitioned,
                skipped_reason=skipped_reason,
            )

        lots = list(
            Lot.objects.select_for_update(of=("self",))
            .select_related("auction", "winner", "winning_bid")
            .filter(auction=auction)
            .exclude(status=LotStatus.CANCELLED)
            .order_by("id")
        )
        winner_results = [_finalise_locked_lot_outcome(lot=lot, now=now) for lot in lots]

    lots_processed = sum(1 for result in winner_results if not result.skipped)
    if transitioned:
        emit_notification_event(
            event_type="auction_ended",
            recipient=auction.created_by,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={
                "lot_id": None,
                "auction_id": auction.id,
                "lots_processed": lots_processed,
                "source": "sync_auction_lifecycle",
            },
        )

    return AuctionLifecycleResult(
        auction_id=auction.id,
        title=auction.title,
        status=auction.status,
        transitioned=transitioned,
        lots_processed=lots_processed,
        winners=winner_results,
        skipped_reason=None if transitioned or lots_processed else "already_synced",
    )


def sync_all_lifecycle(*, now=None, limit: int | None = None) -> dict:
    now = current_lifecycle_time(now)
    opened = open_due_auctions(now=now, limit=limit)
    closed = close_due_auctions(now=now, limit=limit)
    return {
        "server_now": now,
        "opened": opened,
        "closed": closed,
        "auctions_opened": sum(1 for result in opened if result.transitioned),
        "auctions_closed": sum(1 for result in closed if result.transitioned),
        "lots_processed": sum(result.lots_processed for result in closed),
    }


def open_scheduled_auctions(*, now=None, limit: int | None = None) -> list[AuctionLifecycleResult]:
    return open_due_auctions(now=now, limit=limit)


def activate_scheduled_auction_if_due(auction_id: int, *, now=None) -> AuctionLifecycleResult:
    now = current_lifecycle_time(now)
    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction_id)
        if auction.status == AuctionStatus.LIVE:
            return AuctionLifecycleResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="already_live",
            )
        if auction.status != AuctionStatus.SCHEDULED:
            return AuctionLifecycleResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="not_scheduled",
            )
        if auction.start_time > now:
            return AuctionLifecycleResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="not_due",
            )
        if auction.end_time <= now:
            return AuctionLifecycleResult(
                auction_id=auction.id,
                title=auction.title,
                status=auction.status,
                transitioned=False,
                skipped_reason="already_expired",
            )
        effective_status, transitioned = sync_locked_auction_status(
            auction,
            now=now,
            source="activate_scheduled_auction_if_due",
        )
        return AuctionLifecycleResult(
            auction_id=auction.id,
            title=auction.title,
            status=auction.status,
            transitioned=transitioned and effective_status == AuctionStatus.LIVE,
            skipped_reason=None if transitioned else "already_synced",
        )


def _finalise_locked_lot_outcome(*, lot: Lot, now) -> LotWinnerResult:
    if lot.status == LotStatus.CANCELLED:
        return LotWinnerResult(lot_id=lot.id, result=lot.winner_status, skipped=True, skipped_reason="lot_cancelled")

    if lot.winner_calculated_at:
        _ensure_winner_side_effects(lot=lot)
        return LotWinnerResult(
            lot_id=lot.id,
            result=lot.winner_status,
            winning_bid_id=lot.winning_bid_id,
            winner_id=lot.winner_id,
            amount=str(lot.winning_bid.amount) if lot.winning_bid else None,
            skipped=True,
            skipped_reason="already_finalised",
        )

    if get_effective_auction_status(lot.auction, now=now) != AuctionStatus.ENDED:
        return LotWinnerResult(lot_id=lot.id, result=lot.winner_status, skipped=True, skipped_reason="auction_not_ended")

    highest_bid = (
        lot.bids.filter(status=BidStatus.ACCEPTED)
        .select_related("bidder")
        .order_by("-amount", "server_timestamp", "id")
        .first()
    )

    previous_status = lot.status
    metadata = {
        "actor": SYSTEM_ACTOR,
        "lot_id": lot.id,
        "auction_id": lot.auction_id,
        "previous_state": previous_status,
        "previous_status": previous_status,
        "reserve_price": str(lot.reserve_price) if lot.reserve_price is not None else None,
        "reason": "auction_end_time_elapsed",
    }

    if highest_bid is None:
        lot.status = LotStatus.CLOSED
        lot.winner = None
        lot.winning_bid = None
        lot.winner_status = LotWinnerStatus.NO_BIDS
        result = LotWinnerStatus.NO_BIDS
        lifecycle_action = AuditAction.LOT_CLOSED_NO_BIDS
        metadata["reason"] = "no_bids"
    elif lot.reserve_price is not None and highest_bid.amount < lot.reserve_price:
        lot.status = LotStatus.CLOSED
        lot.winner = None
        lot.winning_bid = None
        lot.winner_status = LotWinnerStatus.RESERVE_NOT_MET
        result = LotWinnerStatus.RESERVE_NOT_MET
        lifecycle_action = AuditAction.LOT_CLOSED_AUTOMATICALLY
        metadata.update(
            {
                "reason": "reserve_not_met",
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
        lifecycle_action = AuditAction.LOT_SOLD
        metadata.update(
            {
                "reason": "winning_bid",
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

    outcome_metadata = {
        **metadata,
        "new_state": lot.status,
        "new_status": lot.status,
        "winner_status": lot.winner_status,
    }
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.WINNER_CALCULATED,
        entity_type="lot",
        entity_id=str(lot.id),
        server_timestamp=now,
        metadata=outcome_metadata,
    )
    AuditLog.objects.create(
        actor=None,
        action=lifecycle_action,
        entity_type="lot",
        entity_id=str(lot.id),
        server_timestamp=now,
        metadata=outcome_metadata,
    )
    logger.info(
        "Lot outcome finalised",
        extra={
            "event": "lot_outcome_finalised",
            "auction_id": lot.auction_id,
            "lot_id": lot.id,
            "previous_status": previous_status,
            "new_status": lot.status,
            "winner_status": lot.winner_status,
            "winner_id": lot.winner_id,
            "winning_bid_id": lot.winning_bid_id,
            "server_timestamp": now.isoformat(),
        },
    )

    if lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED:
        _ensure_winner_side_effects(lot=lot)

    return LotWinnerResult(
        lot_id=lot.id,
        result=result,
        winning_bid_id=lot.winning_bid_id,
        winner_id=lot.winner_id,
        amount=str(lot.winning_bid.amount) if lot.winning_bid else None,
    )


def _ensure_winner_side_effects(*, lot: Lot) -> None:
    if lot.winner_status != LotWinnerStatus.WINNER_ASSIGNED:
        return
    if not (lot.winner_id and lot.winning_bid_id):
        return

    ensure_fulfillment_record_for_lot(lot=lot)
    _ensure_winner_notification(lot=lot)


def _ensure_winner_notification(*, lot: Lot) -> OutboundNotification | None:
    if not (lot.winner_id and lot.winning_bid_id):
        return None

    existing = OutboundNotification.objects.filter(
        notification_type="winner_assigned",
        recipient_id=lot.winner_id,
        related_entity_type="lot",
        related_entity_id=str(lot.id),
    ).first()
    if existing:
        return existing

    return emit_notification_event(
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


def _audit_auction_opened(*, auction: Auction, previous_status: str, now, source: str) -> None:
    metadata = {
        "actor": SYSTEM_ACTOR,
        "auction_id": auction.id,
        "lot_id": None,
        "previous_state": previous_status,
        "previous_status": previous_status,
        "new_state": AuctionStatus.LIVE,
        "new_status": AuctionStatus.LIVE,
        "start_time": auction.start_time.isoformat(),
        "end_time": auction.end_time.isoformat(),
        "reason": "start_time_elapsed",
        "source": source,
        "updated_by": source,
        "lifecycle_event": "auction_activated",
    }
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_OPENED_AUTOMATICALLY,
        entity_type="auction",
        entity_id=str(auction.id),
        server_timestamp=now,
        metadata=metadata,
    )
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_UPDATED,
        entity_type="auction",
        entity_id=str(auction.id),
        server_timestamp=now,
        metadata=metadata,
    )
    logger.info(
        "Auction opened automatically",
        extra={
            "event": "auction_opened_automatically",
            "auction_id": auction.id,
            "previous_status": previous_status,
            "new_status": AuctionStatus.LIVE,
            "server_timestamp": now.isoformat(),
        },
    )


def _audit_auction_closed(*, auction: Auction, previous_status: str, now, source: str) -> None:
    metadata = {
        "actor": SYSTEM_ACTOR,
        "auction_id": auction.id,
        "lot_id": None,
        "previous_state": previous_status,
        "previous_status": previous_status,
        "new_state": AuctionStatus.ENDED,
        "new_status": AuctionStatus.ENDED,
        "start_time": auction.start_time.isoformat(),
        "end_time": auction.end_time.isoformat(),
        "reason": "end_time_elapsed",
        "source": source,
        "closed_by": source,
    }
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_CLOSED_AUTOMATICALLY,
        entity_type="auction",
        entity_id=str(auction.id),
        server_timestamp=now,
        metadata=metadata,
    )
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.AUCTION_ENDED,
        entity_type="auction",
        entity_id=str(auction.id),
        server_timestamp=now,
        metadata=metadata,
    )
    logger.info(
        "Auction closed automatically",
        extra={
            "event": "auction_closed_automatically",
            "auction_id": auction.id,
            "previous_status": previous_status,
            "new_status": AuctionStatus.ENDED,
            "server_timestamp": now.isoformat(),
        },
    )


def _audit_lifecycle_noop(*, job_name: str, now, seen: int, transitioned: int, errors: int) -> None:
    if seen or transitioned or errors:
        return
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.LIFECYCLE_JOB_NOOP,
        entity_type="job",
        entity_id=job_name,
        server_timestamp=now,
        metadata={
            "actor": SYSTEM_ACTOR,
            "job_name": job_name,
            "reason": "no_due_records",
            "auctions_seen": seen,
            "auctions_transitioned": transitioned,
            "errors": errors,
        },
    )


def _record_job_failure(*, job_name: str, entity_type: str, entity_id: str, error: Exception, now) -> None:
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.JOB_FAILED,
        entity_type=entity_type,
        entity_id=entity_id,
        server_timestamp=now,
        metadata={
            "actor": SYSTEM_ACTOR,
            "job_name": job_name,
            "error_type": type(error).__name__,
            "reason": "record_processing_failed",
        },
    )
    logger.exception(
        "Lifecycle job failed for one record",
        extra={
            "event": "job_failed",
            "job_name": job_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "error_type": type(error).__name__,
        },
    )


def _not_ended_skip_reason(*, auction: Auction, effective_status: str, now) -> str:
    if auction.status == AuctionStatus.CANCELLED:
        return "auction_cancelled"
    if auction.status == AuctionStatus.DRAFT:
        return "auction_draft"
    if effective_status == AuctionStatus.SCHEDULED and auction.start_time > now:
        return "not_due"
    if effective_status == AuctionStatus.LIVE:
        return "auction_live"
    return "auction_not_finalizable"
