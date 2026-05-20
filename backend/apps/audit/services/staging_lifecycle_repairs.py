from dataclasses import dataclass
import os

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.audit.services.staging_diagnostics import mask_email
from apps.auctions.models import Auction, AuctionStatus, Bid, BidStatus, Lot, LotStatus, LotWinnerStatus
from apps.auctions.services.lifecycle import (
    ENDED_AUCTION_STATUS_ALIASES,
    LIVE_AUCTION_STATUS_ALIASES,
    _finalise_locked_lot_outcome,
    get_effective_auction_status,
)

REPAIR_SOURCE = "staging_repair_lifecycle_issues"


@dataclass(frozen=True)
class RepairOperation:
    action: str
    target_type: str
    target_id: int
    status: str
    reason: str
    before: dict
    after: dict | None = None


def apply_allowed_in_current_environment() -> bool:
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    render_service_name = os.environ.get("RENDER_SERVICE_NAME", "").strip().lower()
    return environment == "staging" or "staging" in render_service_name


def plan_lifecycle_repairs(*, now=None, lock_rows: bool = False) -> list[RepairOperation]:
    now = now or timezone.now()
    # Retain lock_rows for compatibility with older callers, but planning is
    # intentionally unlocked. Apply mode locks concrete target rows by primary
    # key before revalidating and writing.
    _ = lock_rows
    operations = []
    operations.extend(plan_auction_status_repairs(now=now))
    operations.extend(plan_sold_lot_winner_repairs(now=now))
    operations.extend(plan_open_lot_finalisation_repairs(now=now))
    return operations


def apply_lifecycle_repairs(*, now=None) -> list[RepairOperation]:
    now = now or timezone.now()
    candidate_operations = plan_lifecycle_repairs(now=now)
    with transaction.atomic():
        applied = []
        for operation in candidate_operations:
            if operation.status != "planned":
                applied.append(operation)
                continue
            if operation.action == "set_auction_status_ended":
                applied.append(apply_auction_status_repair(operation=operation, now=now))
                continue
            if operation.action == "set_sold_lot_winner_from_highest_accepted_bid":
                applied.append(apply_sold_lot_winner_repair(operation=operation, now=now))
                continue
            if operation.action in {
                "finalise_open_lot_in_ended_auction",
                "close_sold_lot_without_valid_accepted_bid",
            }:
                applied.append(apply_lot_outcome_finalisation_repair(operation=operation, now=now))
                continue
            applied.append(operation)
        return applied


def plan_auction_status_repairs(*, now) -> list[RepairOperation]:
    queryset = Auction.objects.filter(status__in=LIVE_AUCTION_STATUS_ALIASES).order_by("id")

    operations = []
    for auction in queryset:
        effective_status = get_effective_auction_status(auction, now=now)
        if effective_status != AuctionStatus.ENDED:
            continue
        before = auction_snapshot(auction, effective_status=effective_status)
        after = {**before, "status": AuctionStatus.ENDED, "effective_status": effective_status}
        operations.append(
            RepairOperation(
                action="set_auction_status_ended",
                target_type="auction",
                target_id=auction.id,
                status="planned",
                reason="auction_stored_live_but_effective_ended",
                before=before,
                after=after,
            )
        )
    return operations


def plan_sold_lot_winner_repairs(*, now) -> list[RepairOperation]:
    queryset = (
        Lot.objects.select_related("auction", "winner", "winning_bid")
        .filter(status=LotStatus.SOLD)
        .filter(
            Q(winner_id__isnull=True)
            | Q(winning_bid_id__isnull=True)
            | ~Q(winner_status=LotWinnerStatus.WINNER_ASSIGNED)
        )
        .order_by("auction_id", "id")
    )

    operations = []
    for lot in queryset:
        effective_auction_status = get_effective_auction_status(lot.auction, now=now)
        before = lot_snapshot(lot, effective_auction_status=effective_auction_status)
        if lot.status == LotStatus.CANCELLED or lot.auction.status == AuctionStatus.CANCELLED:
            operations.append(
                RepairOperation(
                    action="skip_cancelled_record",
                    target_type="lot",
                    target_id=lot.id,
                    status="unrepaired",
                    reason="cancelled_records_are_not_repaired",
                    before=before,
                )
            )
            continue
        if effective_auction_status != AuctionStatus.ENDED:
            operations.append(
                RepairOperation(
                    action="skip_not_effectively_ended",
                    target_type="lot",
                    target_id=lot.id,
                    status="unrepaired",
                    reason="auction_not_effectively_ended",
                    before=before,
                )
            )
            continue

        winning_bid = highest_accepted_bid(lot)
        if winning_bid is None:
            after = finalised_lot_after_snapshot(lot, before=before)
            operations.append(
                RepairOperation(
                    action="close_sold_lot_without_valid_accepted_bid",
                    target_type="lot",
                    target_id=lot.id,
                    status="planned",
                    reason="no_valid_accepted_bid",
                    before=before,
                    after=after,
                )
            )
            continue

        after = {
            **before,
            "winning_bid_id": winning_bid.id,
            "winner_id": winning_bid.bidder_id,
            "winner_email": mask_email(winning_bid.bidder.email),
            "winner_status": LotWinnerStatus.WINNER_ASSIGNED,
        }
        operations.append(
            RepairOperation(
                action="set_sold_lot_winner_from_highest_accepted_bid",
                target_type="lot",
                target_id=lot.id,
                status="planned",
                reason="sold_lot_missing_winner_or_winning_bid",
                before=before,
                after=after,
            )
        )
    return operations


def plan_open_lot_finalisation_repairs(*, now) -> list[RepairOperation]:
    queryset = (
        Lot.objects.select_related("auction", "winner", "winning_bid")
        .filter(
            status=LotStatus.OPEN,
            auction__status__in=(*LIVE_AUCTION_STATUS_ALIASES, *ENDED_AUCTION_STATUS_ALIASES),
        )
        .order_by("auction_id", "id")
    )

    operations = []
    for lot in queryset:
        effective_auction_status = get_effective_auction_status(lot.auction, now=now)
        if effective_auction_status != AuctionStatus.ENDED:
            continue
        before = lot_snapshot(lot, effective_auction_status=effective_auction_status)
        after = finalised_lot_after_snapshot(lot, before=before)
        operations.append(
            RepairOperation(
                action="finalise_open_lot_in_ended_auction",
                target_type="lot",
                target_id=lot.id,
                status="planned",
                reason="open_lot_inside_effectively_ended_auction",
                before=before,
                after=after,
            )
        )
    return operations


def apply_auction_status_repair(*, operation: RepairOperation, now) -> RepairOperation:
    auction = Auction.objects.select_for_update().get(pk=operation.target_id)
    effective_status = get_effective_auction_status(auction, now=now)
    before = auction_snapshot(auction, effective_status=effective_status)
    if auction.status == AuctionStatus.ENDED:
        return RepairOperation(**{**operation.__dict__, "status": "skipped", "reason": "already_repaired", "before": before, "after": before})
    if auction.status not in LIVE_AUCTION_STATUS_ALIASES or effective_status != AuctionStatus.ENDED:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "state_changed_before_apply", "before": before, "after": None})

    auction.status = AuctionStatus.ENDED
    auction.save(update_fields=("status", "updated_at"))
    auction.refresh_from_db()
    after = auction_snapshot(auction, effective_status=get_effective_auction_status(auction, now=now))
    write_repair_audit(operation=operation, before=before, after=after, now=now)
    return RepairOperation(**{**operation.__dict__, "status": "applied", "before": before, "after": after})


def apply_sold_lot_winner_repair(*, operation: RepairOperation, now) -> RepairOperation:
    lot, auction = lock_lot_and_auction_for_repair(operation)
    effective_auction_status = get_effective_auction_status(lot.auction, now=now)
    before = lot_snapshot(lot, effective_auction_status=effective_auction_status)
    if not sold_lot_needs_winner_repair(lot):
        return RepairOperation(**{**operation.__dict__, "status": "skipped", "reason": "already_repaired", "before": before, "after": before})
    if lot.status == LotStatus.CANCELLED or lot.auction.status == AuctionStatus.CANCELLED:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "cancelled_records_are_not_repaired", "before": before, "after": None})
    if effective_auction_status != AuctionStatus.ENDED:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "auction_not_effectively_ended", "before": before, "after": None})

    winning_bid = highest_accepted_bid(lot)
    if winning_bid is None:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "no_valid_accepted_bid", "before": before, "after": None})

    lot.winning_bid = winning_bid
    lot.winner = winning_bid.bidder
    lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
    lot.save(update_fields=("winning_bid", "winner", "winner_status", "updated_at"))
    lot.refresh_from_db()
    lot.auction = auction
    after = lot_snapshot(lot, effective_auction_status=get_effective_auction_status(lot.auction, now=now))
    write_repair_audit(operation=operation, before=before, after=after, now=now)
    return RepairOperation(**{**operation.__dict__, "status": "applied", "before": before, "after": after})


def apply_lot_outcome_finalisation_repair(*, operation: RepairOperation, now) -> RepairOperation:
    lot, auction = lock_lot_and_auction_for_repair(operation)
    effective_auction_status = get_effective_auction_status(lot.auction, now=now)
    before = lot_snapshot(lot, effective_auction_status=effective_auction_status)
    if lot.status == LotStatus.CANCELLED or lot.auction.status == AuctionStatus.CANCELLED:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "cancelled_records_are_not_repaired", "before": before, "after": None})
    if effective_auction_status != AuctionStatus.ENDED:
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "auction_not_effectively_ended", "before": before, "after": None})
    if operation.action == "finalise_open_lot_in_ended_auction" and lot.status != LotStatus.OPEN:
        if final_lot_outcome_is_complete(lot):
            return RepairOperation(**{**operation.__dict__, "status": "skipped", "reason": "already_repaired", "before": before, "after": before})
        return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "state_changed_before_apply", "before": before, "after": None})
    if operation.action == "close_sold_lot_without_valid_accepted_bid":
        if not sold_lot_needs_winner_repair(lot):
            return RepairOperation(**{**operation.__dict__, "status": "skipped", "reason": "already_repaired", "before": before, "after": before})
        if lot.status != LotStatus.SOLD:
            return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "state_changed_before_apply", "before": before, "after": None})
        if highest_accepted_bid(lot) is not None:
            return RepairOperation(**{**operation.__dict__, "status": "unrepaired", "reason": "valid_accepted_bid_found_before_apply", "before": before, "after": None})

    result = _finalise_locked_lot_outcome(lot=lot, now=now)
    lot.refresh_from_db()
    lot.auction = auction
    after = lot_snapshot(lot, effective_auction_status=get_effective_auction_status(lot.auction, now=now))
    if result.skipped:
        return RepairOperation(**{**operation.__dict__, "status": "skipped", "reason": result.skipped_reason or "already_repaired", "before": before, "after": after})
    write_repair_audit(operation=operation, before=before, after=after, now=now)
    return RepairOperation(**{**operation.__dict__, "status": "applied", "before": before, "after": after})


def lock_lot_and_auction_for_repair(operation: RepairOperation) -> tuple[Lot, Auction]:
    planned_auction_id = operation.before.get("auction_id")
    auction = (
        Auction.objects.select_for_update().get(pk=planned_auction_id)
        if planned_auction_id
        else None
    )
    lot = Lot.objects.select_for_update().get(pk=operation.target_id)
    if auction is None or lot.auction_id != auction.pk:
        auction = Auction.objects.select_for_update().get(pk=lot.auction_id)
    lot.auction = auction
    return lot, auction


def sold_lot_needs_winner_repair(lot: Lot) -> bool:
    return (
        lot.status == LotStatus.SOLD
        and (
            not lot.winner_id
            or not lot.winning_bid_id
            or lot.winner_status != LotWinnerStatus.WINNER_ASSIGNED
        )
    )


def final_lot_outcome_is_complete(lot: Lot) -> bool:
    if lot.status == LotStatus.SOLD:
        return bool(
            lot.winner_id
            and lot.winning_bid_id
            and lot.winner_status == LotWinnerStatus.WINNER_ASSIGNED
        )
    if lot.status == LotStatus.CLOSED:
        return (
            lot.winner_id is None
            and lot.winning_bid_id is None
            and lot.winner_status in {LotWinnerStatus.NO_BIDS, LotWinnerStatus.RESERVE_NOT_MET}
        )
    return False


def highest_accepted_bid(lot: Lot) -> Bid | None:
    return (
        lot.bids.filter(status=BidStatus.ACCEPTED)
        .select_related("bidder")
        .order_by("-amount", "server_timestamp", "id")
        .first()
    )


def finalised_lot_after_snapshot(lot: Lot, *, before: dict) -> dict:
    winning_bid = highest_accepted_bid(lot)
    after = {**before, "winner_calculated_at": "set_on_apply"}
    if winning_bid is None:
        after.update(
            {
                "status": LotStatus.CLOSED,
                "winning_bid_id": None,
                "winner_id": None,
                "winner_email": None,
                "winner_status": LotWinnerStatus.NO_BIDS,
            }
        )
        return after
    if lot.reserve_price is not None and winning_bid.amount < lot.reserve_price:
        after.update(
            {
                "status": LotStatus.CLOSED,
                "winning_bid_id": None,
                "winner_id": None,
                "winner_email": None,
                "winner_status": LotWinnerStatus.RESERVE_NOT_MET,
            }
        )
        return after

    after.update(
        {
            "status": LotStatus.SOLD,
            "winning_bid_id": winning_bid.id,
            "winner_id": winning_bid.bidder_id,
            "winner_email": mask_email(winning_bid.bidder.email),
            "winner_status": LotWinnerStatus.WINNER_ASSIGNED,
        }
    )
    return after


def write_repair_audit(*, operation: RepairOperation, before: dict, after: dict, now) -> None:
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.ADMIN_ACTION,
        entity_type=operation.target_type,
        entity_id=str(operation.target_id),
        server_timestamp=now,
        metadata={
            "source": REPAIR_SOURCE,
            "repair_action": operation.action,
            "reason": operation.reason,
            "before": before,
            "after": after,
        },
    )


def auction_snapshot(auction: Auction, *, effective_status: str) -> dict:
    return {
        "auction_id": auction.id,
        "title": auction.title,
        "status": auction.status,
        "effective_status": effective_status,
        "start_time": iso_or_none(auction.start_time),
        "end_time": iso_or_none(auction.end_time),
        "updated_at": iso_or_none(auction.updated_at),
    }


def lot_snapshot(lot: Lot, *, effective_auction_status: str) -> dict:
    return {
        "lot_id": lot.id,
        "auction_id": lot.auction_id,
        "auction_status": lot.auction.status,
        "auction_effective_status": effective_auction_status,
        "title": lot.title,
        "status": lot.status,
        "current_price": str(lot.current_price),
        "winning_bid_id": lot.winning_bid_id,
        "winner_id": lot.winner_id,
        "winner_email": mask_email(lot.winner.email) if lot.winner_id else None,
        "winner_status": lot.winner_status,
        "winner_calculated_at": iso_or_none(lot.winner_calculated_at),
        "updated_at": iso_or_none(lot.updated_at),
    }


def iso_or_none(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
