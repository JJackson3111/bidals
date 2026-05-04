from dataclasses import dataclass
import logging

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import FulfillmentRecord, FulfillmentStatus, Lot
from apps.auctions.services.notifications import emit_notification_event

logger = logging.getLogger(__name__)


NOTIFY_ON_STATUS = {
    FulfillmentStatus.WINNER_CONFIRMED: "winner_confirmed",
    FulfillmentStatus.SELLER_CONTACTED: "seller_contacted",
    FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY: "awaiting_collection_or_delivery",
    FulfillmentStatus.COMPLETED: "fulfillment_completed",
    FulfillmentStatus.CANCELLED: "fulfillment_cancelled",
    FulfillmentStatus.DISPUTED: "fulfillment_disputed",
}

ALLOWED_TRANSITIONS = {
    FulfillmentStatus.PENDING_CONFIRMATION: (
        FulfillmentStatus.WINNER_CONFIRMED,
        FulfillmentStatus.SELLER_CONTACTED,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.DISPUTED,
    ),
    FulfillmentStatus.WINNER_CONFIRMED: (
        FulfillmentStatus.SELLER_CONTACTED,
        FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.DISPUTED,
    ),
    FulfillmentStatus.SELLER_CONTACTED: (
        FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY,
        FulfillmentStatus.COMPLETED,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.DISPUTED,
    ),
    FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY: (
        FulfillmentStatus.COMPLETED,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.DISPUTED,
    ),
    FulfillmentStatus.COMPLETED: (),
    FulfillmentStatus.CANCELLED: (),
    FulfillmentStatus.DISPUTED: (
        FulfillmentStatus.COMPLETED,
        FulfillmentStatus.CANCELLED,
        FulfillmentStatus.SELLER_CONTACTED,
    ),
}


class FulfillmentTransitionError(Exception):
    def __init__(self, *, old_status: str, new_status: str, allowed_statuses: tuple[str, ...]):
        self.old_status = old_status
        self.new_status = new_status
        self.allowed_statuses = allowed_statuses
        super().__init__(
            f"Invalid fulfillment transition from {old_status} to {new_status}."
        )


def get_allowed_fulfillment_transitions(status: str) -> tuple[str, ...]:
    return tuple(ALLOWED_TRANSITIONS.get(status, ()))


@dataclass(frozen=True)
class FulfillmentUpdateResult:
    record: FulfillmentRecord
    changed_fields: list[str]
    old_status: str
    new_status: str


def ensure_fulfillment_record_for_lot(
    *,
    lot: Lot,
    actor=None,
    source: str = "winner_calculation",
    metadata_extra: dict | None = None,
) -> FulfillmentRecord | None:
    if not (lot.winner_id and lot.winning_bid_id):
        return None

    record, created = FulfillmentRecord.objects.get_or_create(
        lot=lot,
        defaults={
            "auction": lot.auction,
            "winning_bid": lot.winning_bid,
            "winner": lot.winner,
        },
    )
    if created:
        metadata = _audit_metadata(record, old_status=None, new_status=record.status)
        metadata["source"] = source
        if metadata_extra:
            metadata.update(metadata_extra)
        AuditLog.objects.create(
            actor=actor,
            action=AuditAction.FULFILLMENT_CREATED,
            entity_type="fulfillment",
            entity_id=str(record.id),
            metadata=metadata,
        )
        logger.info(
            "Fulfillment record created",
            extra={
                "event": "fulfillment_created",
                "fulfillment_id": record.id,
                "auction_id": record.auction_id,
                "lot_id": record.lot_id,
                "winner_id": record.winner_id,
                "status": record.status,
            },
        )
    return record


def update_fulfillment_record(*, record_id: int, actor, updates: dict) -> FulfillmentUpdateResult:
    transition_error = None
    changed_fields = []
    with transaction.atomic():
        record = (
            FulfillmentRecord.objects.select_for_update()
            .select_related("auction", "lot", "winner", "winning_bid")
            .get(pk=record_id)
        )
        old_status = record.status
        requested_status = updates.get("status")
        if requested_status and requested_status != old_status:
            allowed_statuses = get_allowed_fulfillment_transitions(old_status)
            if requested_status not in allowed_statuses:
                _audit_invalid_transition(
                    actor=actor,
                    record=record,
                    old_status=old_status,
                    attempted_status=requested_status,
                    allowed_statuses=allowed_statuses,
                )
                transition_error = FulfillmentTransitionError(
                    old_status=old_status,
                    new_status=requested_status,
                    allowed_statuses=allowed_statuses,
                )

        for field in (
            "status",
            "confirmation_notes",
            "seller_notes",
            "admin_notes",
            "public_winner_message",
        ):
            if transition_error:
                continue
            if field not in updates:
                continue
            new_value = updates[field]
            if getattr(record, field) != new_value:
                setattr(record, field, new_value)
                changed_fields.append(field)

        now = timezone.now()
        if changed_fields:
            record.last_follow_up_at = now
        if "status" in changed_fields and record.status == FulfillmentStatus.COMPLETED:
            record.completed_at = now
        elif "status" in changed_fields and old_status == FulfillmentStatus.COMPLETED:
            record.completed_at = None

        if changed_fields:
            record.save(
                update_fields=(
                    "status",
                    "confirmation_notes",
                    "seller_notes",
                    "admin_notes",
                    "public_winner_message",
                    "last_follow_up_at",
                    "completed_at",
                    "updated_at",
                )
            )
            _audit_fulfillment_changes(
                actor=actor,
                record=record,
                changed_fields=changed_fields,
                old_status=old_status,
            )

    if transition_error:
        raise transition_error

    if "status" in changed_fields and record.status in NOTIFY_ON_STATUS:
        emit_notification_event(
            event_type=NOTIFY_ON_STATUS[record.status],
            recipient=record.winner,
            entity_type="fulfillment",
            entity_id=str(record.id),
            metadata={
                "fulfillment_id": record.id,
                "auction_id": record.auction_id,
                "lot_id": record.lot_id,
                "winner_id": record.winner_id,
                "status": record.status,
                "old_status": old_status,
            },
        )

    return FulfillmentUpdateResult(
        record=record,
        changed_fields=changed_fields,
        old_status=old_status,
        new_status=record.status,
    )


def _audit_invalid_transition(
    *,
    actor,
    record: FulfillmentRecord,
    old_status: str,
    attempted_status: str,
    allowed_statuses: tuple[str, ...],
) -> None:
    AuditLog.objects.create(
        actor=actor,
        action=AuditAction.FULFILLMENT_INVALID_TRANSITION,
        entity_type="fulfillment",
        entity_id=str(record.id),
        metadata={
            **_audit_metadata(record, old_status=old_status, new_status=old_status),
            "attempted_status": attempted_status,
            "allowed_statuses": list(allowed_statuses),
            "actor_id": actor.id if actor else None,
            "reason": "transition_not_allowed",
        },
    )
    logger.warning(
        "Invalid fulfillment transition rejected",
        extra={
            "event": "fulfillment_invalid_transition",
            "fulfillment_id": record.id,
            "auction_id": record.auction_id,
            "lot_id": record.lot_id,
            "winner_id": record.winner_id,
            "old_status": old_status,
            "attempted_status": attempted_status,
            "allowed_statuses": list(allowed_statuses),
        },
    )


def _audit_fulfillment_changes(*, actor, record: FulfillmentRecord, changed_fields: list[str], old_status: str) -> None:
    metadata = _audit_metadata(record, old_status=old_status, new_status=record.status)
    metadata["updated_fields"] = changed_fields
    actor_id = actor.id if actor else None
    metadata["actor_id"] = actor_id

    if "status" in changed_fields:
        action = {
            FulfillmentStatus.COMPLETED: AuditAction.FULFILLMENT_COMPLETED,
            FulfillmentStatus.CANCELLED: AuditAction.FULFILLMENT_CANCELLED,
            FulfillmentStatus.DISPUTED: AuditAction.FULFILLMENT_DISPUTED,
        }.get(record.status, AuditAction.FULFILLMENT_STATUS_CHANGED)
        AuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type="fulfillment",
            entity_id=str(record.id),
            metadata=metadata,
        )

    note_action_by_field = {
        "confirmation_notes": AuditAction.FULFILLMENT_CONFIRMATION_NOTES_UPDATED,
        "seller_notes": AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED,
        "admin_notes": AuditAction.FULFILLMENT_ADMIN_NOTES_UPDATED,
    }
    for field, action in note_action_by_field.items():
        if field in changed_fields:
            AuditLog.objects.create(
                actor=actor,
                action=action,
                entity_type="fulfillment",
                entity_id=str(record.id),
                metadata={
                    **metadata,
                    "note_field": field,
                },
            )

    logger.info(
        "Fulfillment record updated",
        extra={
            "event": "fulfillment_updated",
            "fulfillment_id": record.id,
            "auction_id": record.auction_id,
            "lot_id": record.lot_id,
            "winner_id": record.winner_id,
            "old_status": old_status,
            "new_status": record.status,
            "updated_fields": changed_fields,
        },
    )


def _audit_metadata(record: FulfillmentRecord, *, old_status: str | None, new_status: str) -> dict:
    return {
        "fulfillment_id": record.id,
        "auction_id": record.auction_id,
        "lot_id": record.lot_id,
        "winning_bid_id": record.winning_bid_id,
        "winner_id": record.winner_id,
        "old_status": old_status,
        "new_status": new_status,
    }
