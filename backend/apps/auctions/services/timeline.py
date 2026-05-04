from django.db.models import Q

from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import FulfillmentRecord


DASHBOARD_TIMELINE_ACTIONS = {
    AuditAction.FULFILLMENT_CREATED,
    AuditAction.FULFILLMENT_STATUS_CHANGED,
    AuditAction.FULFILLMENT_INVALID_TRANSITION,
    AuditAction.FULFILLMENT_CONFIRMATION_NOTES_UPDATED,
    AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED,
    AuditAction.FULFILLMENT_ADMIN_NOTES_UPDATED,
    AuditAction.FULFILLMENT_COMPLETED,
    AuditAction.FULFILLMENT_CANCELLED,
    AuditAction.FULFILLMENT_DISPUTED,
    AuditAction.NOTIFICATION_EVENT,
    AuditAction.WINNER_CALCULATED,
    AuditAction.WINNER_OUTCOME_BACKFILLED,
    AuditAction.OUTCOME_REPAIR_REQUESTED,
    AuditAction.OUTCOME_REPAIR_APPROVED,
    AuditAction.OUTCOME_REPAIR_REJECTED,
    AuditAction.OUTCOME_REPAIR_APPLIED,
    AuditAction.OUTCOME_REPAIR_CANCELLED,
}

PUBLIC_TIMELINE_ACTIONS = {
    AuditAction.FULFILLMENT_CREATED,
    AuditAction.FULFILLMENT_STATUS_CHANGED,
    AuditAction.FULFILLMENT_COMPLETED,
    AuditAction.FULFILLMENT_CANCELLED,
    AuditAction.FULFILLMENT_DISPUTED,
    AuditAction.NOTIFICATION_EVENT,
}


def fulfillment_timeline(record: FulfillmentRecord, *, public: bool = False):
    actions = PUBLIC_TIMELINE_ACTIONS if public else DASHBOARD_TIMELINE_ACTIONS
    filters = (
        Q(entity_type="fulfillment", entity_id=str(record.id))
        | Q(metadata__fulfillment_id=record.id)
        | Q(entity_type="lot", entity_id=str(record.lot_id), action__in=actions)
        | Q(metadata__lot_id=record.lot_id, action__in=actions)
    )
    queryset = (
        AuditLog.objects.select_related("actor")
        .filter(filters, action__in=actions)
        .order_by("server_timestamp", "id")
    )
    if public:
        queryset = queryset.exclude(action=AuditAction.FULFILLMENT_INVALID_TRANSITION).exclude(
            action__in=(
                AuditAction.FULFILLMENT_CONFIRMATION_NOTES_UPDATED,
                AuditAction.FULFILLMENT_SELLER_NOTES_UPDATED,
                AuditAction.FULFILLMENT_ADMIN_NOTES_UPDATED,
            )
        )
    return queryset


def serialize_timeline_event(log: AuditLog, *, public: bool = False) -> dict:
    metadata = log.metadata or {}
    event = {
        "id": log.id,
        "event_type": log.action,
        "actor_username": "" if public else (log.actor.username if log.actor else "System"),
        "old_status": metadata.get("old_status"),
        "new_status": metadata.get("new_status") or metadata.get("winner_status") or metadata.get("status"),
        "notification_type": metadata.get("event_type") if log.action == AuditAction.NOTIFICATION_EVENT else "",
        "created_at": log.server_timestamp,
    }
    if not public:
        event.update(
            {
                "note_field": metadata.get("note_field", ""),
                "attempted_status": metadata.get("attempted_status", ""),
                "repair_id": metadata.get("repair_id"),
                "winning_bid_id": metadata.get("winning_bid_id"),
                "winner_id": metadata.get("winner_id"),
            }
        )
    return event
