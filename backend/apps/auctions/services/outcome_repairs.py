from dataclasses import dataclass
import logging

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import (
    Bid,
    BidStatus,
    FulfillmentRecord,
    FulfillmentStatus,
    Lot,
    LotStatus,
    LotWinnerStatus,
    OutcomeRepairComment,
    OutcomeRepairRequest,
    OutcomeRepairStatus,
)
from apps.auctions.services.notifications import emit_notification_event

logger = logging.getLogger(__name__)


class OutcomeRepairError(Exception):
    pass


@dataclass(frozen=True)
class OutcomeRepairResult:
    repair: OutcomeRepairRequest


def create_outcome_repair_request(*, actor, lot_id: int, requested_winning_bid_id: int, reason: str) -> OutcomeRepairRequest:
    reason = (reason or "").strip()
    if not reason:
        raise OutcomeRepairError("A repair reason is required.")

    lot = Lot.objects.select_related("auction", "winner", "winning_bid").get(pk=lot_id)
    bid = Bid.objects.select_related("bidder", "lot").get(pk=requested_winning_bid_id)
    _validate_requested_bid(lot=lot, bid=bid)

    repair = OutcomeRepairRequest.objects.create(
        lot=lot,
        auction=lot.auction,
        current_outcome=lot.winner_status,
        requested_winning_bid=bid,
        requested_winner=bid.bidder,
        reason=reason,
        requested_by=actor,
        metadata={
            "old_winner_id": lot.winner_id,
            "old_winning_bid_id": lot.winning_bid_id,
            "old_winner_status": lot.winner_status,
            "old_lot_status": lot.status,
            "requested_amount": str(bid.amount),
        },
    )
    _audit_repair(
        action=AuditAction.OUTCOME_REPAIR_REQUESTED,
        actor=actor,
        repair=repair,
        metadata_extra={"reason": reason},
    )
    return repair


def approve_outcome_repair(*, repair_id: int, actor, approval_notes: str = "") -> OutcomeRepairRequest:
    repair_for_policy = (
        OutcomeRepairRequest.objects.select_related(
            "lot",
            "requested_winner",
            "requested_winning_bid",
            "requested_by",
        )
        .get(pk=repair_id)
    )
    if repair_for_policy.status == OutcomeRepairStatus.PENDING_REVIEW and repair_for_policy.requested_by_id == actor.id:
        _audit_repair(
            action=AuditAction.OUTCOME_REPAIR_INVALID_APPROVAL,
            actor=actor,
            repair=repair_for_policy,
            metadata_extra={
                "reason": "requester_cannot_approve_own_repair",
                "requested_by_id": repair_for_policy.requested_by_id,
                "approver_id": actor.id,
            },
        )
        raise OutcomeRepairError("A different admin must approve this repair request.")

    with transaction.atomic():
        repair = (
            OutcomeRepairRequest.objects.select_for_update()
            .select_related("lot", "requested_winner", "requested_winning_bid", "requested_by")
            .get(pk=repair_id)
        )
        if repair.status != OutcomeRepairStatus.PENDING_REVIEW:
            raise OutcomeRepairError("Only pending repair requests can be approved.")
        if repair.requested_by_id == actor.id:
            raise OutcomeRepairError("A different admin must approve this repair request.")
        repair.status = OutcomeRepairStatus.APPROVED
        repair.reviewed_by = actor
        repair.reviewed_at = timezone.now()
        repair.approval_notes = (approval_notes or "").strip()
        repair.save(update_fields=("status", "reviewed_by", "reviewed_at", "approval_notes", "updated_at"))
        _audit_repair(
            action=AuditAction.OUTCOME_REPAIR_APPROVED,
            actor=actor,
            repair=repair,
            metadata_extra={"approval_notes_present": bool(repair.approval_notes)},
        )
    return repair


def reject_outcome_repair(*, repair_id: int, actor) -> OutcomeRepairRequest:
    with transaction.atomic():
        repair = (
            OutcomeRepairRequest.objects.select_for_update()
            .select_related("lot", "requested_winner", "requested_winning_bid")
            .get(pk=repair_id)
        )
        if repair.status != OutcomeRepairStatus.PENDING_REVIEW:
            raise OutcomeRepairError("Only pending repair requests can be rejected.")
        repair.status = OutcomeRepairStatus.REJECTED
        repair.reviewed_by = actor
        repair.reviewed_at = timezone.now()
        repair.save(update_fields=("status", "reviewed_by", "reviewed_at", "updated_at"))
        _audit_repair(action=AuditAction.OUTCOME_REPAIR_REJECTED, actor=actor, repair=repair)
    return repair


def create_outcome_repair_comment(*, repair_id: int, actor, comment_text: str) -> OutcomeRepairComment:
    comment_text = (comment_text or "").strip()
    if not comment_text:
        raise OutcomeRepairError("A repair comment is required.")

    with transaction.atomic():
        repair = OutcomeRepairRequest.objects.select_related("lot", "auction").get(pk=repair_id)
        comment = OutcomeRepairComment.objects.create(
            repair_request=repair,
            author=actor,
            comment_text=comment_text,
            metadata={
                "repair_id": repair.id,
                "auction_id": repair.auction_id,
                "lot_id": repair.lot_id,
                "actor_id": actor.id if actor else None,
            },
        )
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.OUTCOME_REPAIR_COMMENT_CREATED,
            entity_type="outcome_repair",
            entity_id=str(repair.id),
            metadata={
                "repair_id": repair.id,
                "comment_id": comment.id,
                "auction_id": repair.auction_id,
                "lot_id": repair.lot_id,
                "actor_id": actor.id if actor else None,
            },
        )
    return comment


def apply_outcome_repair(*, repair_id: int, actor) -> OutcomeRepairResult:
    with transaction.atomic():
        repair = (
            OutcomeRepairRequest.objects.select_for_update()
            .select_related("lot", "auction", "requested_winning_bid", "requested_winner")
            .get(pk=repair_id)
        )
        if repair.status != OutcomeRepairStatus.APPROVED:
            raise OutcomeRepairError("Only approved repair requests can be applied.")

        lot = Lot.objects.select_for_update(of=("self",)).select_related("winner", "winning_bid", "auction").get(pk=repair.lot_id)
        bid = Bid.objects.select_related("bidder").get(pk=repair.requested_winning_bid_id)
        _validate_requested_bid(lot=lot, bid=bid)

        old_winner_id = lot.winner_id
        old_winning_bid_id = lot.winning_bid_id
        old_winner_status = lot.winner_status
        old_lot_status = lot.status

        lot.winner = bid.bidder
        lot.winning_bid = bid
        lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
        lot.status = LotStatus.SOLD
        lot.winner_calculated_at = timezone.now()
        lot.save(update_fields=("winner", "winning_bid", "winner_status", "status", "winner_calculated_at", "updated_at"))

        fulfillment = _repair_fulfillment_record(lot=lot, bid=bid, actor=actor, repair=repair)

        repair.status = OutcomeRepairStatus.APPLIED
        repair.applied_by = actor
        repair.applied_at = timezone.now()
        repair.metadata = {
            **repair.metadata,
            "old_winner_id": old_winner_id,
            "old_winning_bid_id": old_winning_bid_id,
            "old_winner_status": old_winner_status,
            "old_lot_status": old_lot_status,
            "new_winner_id": lot.winner_id,
            "new_winning_bid_id": lot.winning_bid_id,
            "new_winner_status": lot.winner_status,
            "new_lot_status": lot.status,
            "fulfillment_id": fulfillment.id,
        }
        repair.save(update_fields=("status", "applied_by", "applied_at", "metadata", "updated_at"))
        _audit_repair(
            action=AuditAction.OUTCOME_REPAIR_APPLIED,
            actor=actor,
            repair=repair,
            metadata_extra={
                "old_winner_id": old_winner_id,
                "old_winning_bid_id": old_winning_bid_id,
                "old_winner_status": old_winner_status,
                "new_winner_id": lot.winner_id,
                "new_winning_bid_id": lot.winning_bid_id,
                "new_winner_status": lot.winner_status,
                "fulfillment_id": fulfillment.id,
            },
        )
        emit_notification_event(
            event_type="outcome_repair_applied",
            recipient=lot.winner,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "repair_id": repair.id,
                "auction_id": lot.auction_id,
                "lot_id": lot.id,
                "winner_id": lot.winner_id,
                "winning_bid_id": lot.winning_bid_id,
                "fulfillment_id": fulfillment.id,
            },
        )
        logger.info(
            "Outcome repair applied",
            extra={
                "event": "outcome_repair_applied",
                "repair_id": repair.id,
                "auction_id": lot.auction_id,
                "lot_id": lot.id,
                "old_winner_id": old_winner_id,
                "new_winner_id": lot.winner_id,
            },
        )
    return OutcomeRepairResult(repair=repair)


def _repair_fulfillment_record(*, lot: Lot, bid: Bid, actor, repair: OutcomeRepairRequest) -> FulfillmentRecord:
    record, created = FulfillmentRecord.objects.get_or_create(
        lot=lot,
        defaults={
            "auction": lot.auction,
            "winning_bid": bid,
            "winner": bid.bidder,
        },
    )
    old_status = record.status
    record.auction = lot.auction
    record.winning_bid = bid
    record.winner = bid.bidder
    record.status = FulfillmentStatus.PENDING_CONFIRMATION
    record.completed_at = None
    record.last_follow_up_at = timezone.now()
    record.public_winner_message = ""
    record.save(
        update_fields=(
            "auction",
            "winning_bid",
            "winner",
            "status",
            "completed_at",
            "last_follow_up_at",
            "public_winner_message",
            "updated_at",
        )
    )
    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.FULFILLMENT_CREATED if created else AuditAction.FULFILLMENT_STATUS_CHANGED,
        entity_type="fulfillment",
        entity_id=str(record.id),
        metadata={
            "fulfillment_id": record.id,
            "auction_id": record.auction_id,
            "lot_id": record.lot_id,
            "winning_bid_id": record.winning_bid_id,
            "winner_id": record.winner_id,
            "repair_id": repair.id,
            "old_status": old_status,
            "new_status": record.status,
            "source": "outcome_repair",
            "actor_id": actor.id if actor else None,
        },
    )
    return record


def _validate_requested_bid(*, lot: Lot, bid: Bid) -> None:
    if bid.lot_id != lot.id:
        raise OutcomeRepairError("Requested winning bid must belong to the lot.")
    if bid.status != BidStatus.ACCEPTED:
        raise OutcomeRepairError("Requested winning bid must be accepted.")


def _audit_repair(*, action: str, actor, repair: OutcomeRepairRequest, metadata_extra: dict | None = None) -> None:
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type="outcome_repair",
        entity_id=str(repair.id),
        metadata={
            "repair_id": repair.id,
            "auction_id": repair.auction_id,
            "lot_id": repair.lot_id,
            "old_winner_id": repair.metadata.get("old_winner_id"),
            "new_winner_id": repair.requested_winner_id,
            "old_winning_bid_id": repair.metadata.get("old_winning_bid_id"),
            "new_winning_bid_id": repair.requested_winning_bid_id,
            "actor_id": actor.id if actor else None,
            "status": repair.status,
            **(metadata_extra or {}),
        },
    )
