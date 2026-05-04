from datetime import timedelta
import csv

from django.conf import settings
from django.http import HttpResponse
from django.db.models import Count
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminRole
from apps.audit.models import AuditAction, AuditLog, NotificationStatus, OutboundNotification
from apps.audit.serializers import AccountNotificationSerializer, AuditLogSerializer, OutboundNotificationSerializer
from apps.audit.safety import metadata_summary
from apps.audit.services.readiness import run_release_check
from apps.auctions.models import Bid, BidRejectionReason, BidStatus, FulfillmentRecord, FulfillmentStatus


class AuditLogViewSet(ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get_queryset(self):
        return _filtered_audit_queryset(self.request.query_params)


class AdminActivityExportView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        queryset = _filtered_audit_queryset(request.query_params).order_by("server_timestamp", "id")
        total_count = queryset.count()
        logs = list(queryset[:10000])
        filters = _admin_export_filters(request.query_params)

        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.ADMIN_ACTIVITY_EXPORTED,
            entity_type="admin_activity_export",
            entity_id=timezone.now().strftime("%Y%m%d%H%M%S"),
            metadata={
                "actor_id": request.user.id,
                "filters": filters,
                "row_count": len(logs),
                "truncated": total_count > len(logs),
                "request_id": getattr(request, "request_id", None),
            },
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="bidals-admin-activity.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "audit_id",
                "admin_user_id",
                "admin_username",
                "action",
                "entity_type",
                "entity_id",
                "server_timestamp",
                "request_id",
                "ip_address",
                "metadata_summary",
            ]
        )
        for log in logs:
            metadata = log.metadata or {}
            writer.writerow(
                [
                    log.id,
                    log.actor_id or "",
                    log.actor.username if log.actor else "System",
                    log.action,
                    log.entity_type,
                    log.entity_id,
                    log.server_timestamp.isoformat(),
                    metadata.get("request_id", ""),
                    metadata.get("ip_address", metadata.get("ip", "")),
                    metadata_summary(metadata),
                ]
            )
        return response


class OperationsSummaryView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        window_minutes = _parse_window_minutes(request.query_params.get("window_minutes"))
        now = timezone.now()
        since = now - timedelta(minutes=window_minutes)

        all_bids = Bid.objects.select_related("bidder", "lot", "lot__auction")
        recent_bids = all_bids.filter(server_timestamp__gte=since)
        recent_audit = AuditLog.objects.select_related("actor").filter(server_timestamp__gte=since)
        recent_errors = recent_audit.filter(
            action=AuditAction.BID_REJECTED,
            metadata__reason=BidRejectionReason.SERVER_ERROR,
        )
        recent_closing_runs = recent_audit.filter(action=AuditAction.AUCTION_CLOSE_RUN)
        recent_winner_calculations = recent_audit.filter(action=AuditAction.WINNER_CALCULATED)
        recent_anomalies = recent_audit.filter(action=AuditAction.BID_ANOMALY_DETECTED)
        recent_alerts = recent_audit.filter(action=AuditAction.ALERT_TRIGGERED)
        recent_job_failures = recent_audit.filter(action=AuditAction.JOB_FAILED)
        recent_notifications = recent_audit.filter(action=AuditAction.NOTIFICATION_EVENT)
        recent_outbound_notifications = OutboundNotification.objects.select_related("recipient").filter(created_at__gte=since)
        recent_fulfillment_audit = recent_audit.filter(action__startswith="fulfillment_")
        fulfillment_records = FulfillmentRecord.objects.all()

        summary = {
            "total_bids": all_bids.count(),
            "accepted_bids": all_bids.filter(status=BidStatus.ACCEPTED).count(),
            "rejected_bids": all_bids.filter(status=BidStatus.REJECTED).count(),
            "recent_accepted_bids": recent_bids.filter(status=BidStatus.ACCEPTED).count(),
            "recent_rejected_bids": recent_bids.filter(status=BidStatus.REJECTED).count(),
            "recent_audit_events": recent_audit.count(),
            "recent_server_bid_errors": recent_errors.count(),
            "suspicious_repeated_failures": _suspicious_failure_count(recent_bids),
            "auction_close_runs": recent_closing_runs.count(),
            "winner_calculations": recent_winner_calculations.count(),
            "bid_anomalies": recent_anomalies.count(),
            "alert_events": recent_alerts.count(),
            "job_failures": recent_job_failures.count(),
            "notification_events": recent_notifications.count(),
            "pending_notifications": recent_outbound_notifications.filter(status=NotificationStatus.PENDING).count(),
            "sent_notifications": recent_outbound_notifications.filter(status=NotificationStatus.SENT).count(),
            "failed_notifications": recent_outbound_notifications.filter(status=NotificationStatus.FAILED).count(),
            "skipped_notifications": recent_outbound_notifications.filter(status=NotificationStatus.SKIPPED).count(),
            "fulfillment_pending_confirmation": fulfillment_records.filter(status=FulfillmentStatus.PENDING_CONFIRMATION).count(),
            "fulfillment_seller_contacted": fulfillment_records.filter(status=FulfillmentStatus.SELLER_CONTACTED).count(),
            "fulfillment_awaiting_collection_or_delivery": fulfillment_records.filter(status=FulfillmentStatus.AWAITING_COLLECTION_OR_DELIVERY).count(),
            "fulfillment_completed": fulfillment_records.filter(status=FulfillmentStatus.COMPLETED).count(),
            "fulfillment_disputed": fulfillment_records.filter(status=FulfillmentStatus.DISPUTED).count(),
            "recent_fulfillment_updates": recent_fulfillment_audit.count(),
        }

        return Response(
            {
                "generated_at": now,
                "window_minutes": window_minutes,
                "thresholds": {
                    "bid_anomaly_reject_threshold": settings.BID_ANOMALY_REJECT_THRESHOLD,
                    "bid_anomaly_rate_limit_threshold": settings.BID_ANOMALY_RATE_LIMIT_THRESHOLD,
                },
                "summary": summary,
                "rejected_by_reason": list(
                    recent_bids.filter(status=BidStatus.REJECTED)
                    .values("rejection_reason")
                    .annotate(count=Count("id"))
                    .order_by("-count", "rejection_reason")
                ),
                "suspicious_repeated_failures": _suspicious_failures(recent_bids),
                "recent_accepted_bids": [
                    _bid_event(bid)
                    for bid in recent_bids.filter(status=BidStatus.ACCEPTED).order_by("-server_timestamp", "-id")[:10]
                ],
                "recent_rejected_bids": [
                    _bid_event(bid)
                    for bid in recent_bids.filter(status=BidStatus.REJECTED).order_by("-server_timestamp", "-id")[:10]
                ],
                "recent_audit_events": AuditLogSerializer(
                    recent_audit.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_server_errors": AuditLogSerializer(
                    recent_errors.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_auction_close_runs": AuditLogSerializer(
                    recent_closing_runs.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_winner_calculations": AuditLogSerializer(
                    recent_winner_calculations.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_anomalies": AuditLogSerializer(
                    recent_anomalies.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_alerts": AuditLogSerializer(
                    recent_alerts.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_job_failures": AuditLogSerializer(
                    recent_job_failures.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_notifications": AuditLogSerializer(
                    recent_notifications.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
                "recent_outbound_notifications": OutboundNotificationSerializer(
                    recent_outbound_notifications.order_by("-created_at", "-id")[:10],
                    many=True,
                ).data,
                "recent_failed_notifications": OutboundNotificationSerializer(
                    recent_outbound_notifications.filter(status=NotificationStatus.FAILED).order_by("-created_at", "-id")[:10],
                    many=True,
                ).data,
                "recent_fulfillment_updates": AuditLogSerializer(
                    recent_fulfillment_audit.order_by("-server_timestamp", "-id")[:10],
                    many=True,
                ).data,
            }
        )


class ReleaseCheckView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        return Response(
            run_release_check(
                actor=request.user,
                request_id=getattr(request, "request_id", None),
            )
        )


class AccountNotificationListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        notifications = (
            OutboundNotification.objects.filter(recipient=request.user)
            .order_by("-created_at", "-id")[:100]
        )
        return Response(
            {
                "unread_count": OutboundNotification.objects.filter(recipient=request.user, read_at__isnull=True).count(),
                "results": AccountNotificationSerializer(notifications, many=True).data,
            }
        )


class AccountNotificationUnreadCountView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        unread_count = OutboundNotification.objects.filter(recipient=request.user, read_at__isnull=True).count()
        return Response({"unread_count": unread_count})


class AccountNotificationReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, pk):
        try:
            notification = OutboundNotification.objects.get(pk=pk, recipient=request.user)
        except OutboundNotification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=404)

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at",))
            AuditLog.objects.create(
                actor=request.user,
                action=AuditAction.NOTIFICATION_MARKED_READ,
                entity_type="notification",
                entity_id=str(notification.id),
                metadata={
                    "notification_id": notification.id,
                    "notification_type": notification.notification_type,
                    "actor_id": request.user.id,
                },
            )
        return Response(AccountNotificationSerializer(notification).data)


class AccountNotificationsMarkAllReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        now = timezone.now()
        updated = OutboundNotification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=now)
        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.NOTIFICATIONS_MARKED_READ,
            entity_type="notification",
            entity_id="bulk",
            metadata={
                "actor_id": request.user.id,
                "count": updated,
            },
        )
        return Response({"marked_read": updated, "unread_count": 0})


def _parse_datetime_query_param(value: str | None, field_name: str):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        raise ValidationError({field_name: "Use an ISO-8601 datetime."})

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _filtered_audit_queryset(params):
    queryset = AuditLog.objects.select_related("actor").all()

    action = params.get("action_type") or params.get("action")
    if action:
        queryset = queryset.filter(action=action)

    entity_type = params.get("entity_type")
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)

    entity_id = params.get("entity_id")
    if entity_id:
        queryset = queryset.filter(entity_id=entity_id)

    actor = params.get("actor")
    if actor:
        if actor.isdigit():
            queryset = queryset.filter(actor_id=int(actor))
        else:
            queryset = queryset.filter(
                Q(actor__username__icontains=actor) | Q(actor__email__icontains=actor)
            )

    bid_status = params.get("bid_status")
    if bid_status == "accepted":
        queryset = queryset.filter(action="bid_accepted")
    elif bid_status == "rejected":
        queryset = queryset.filter(action="bid_rejected")

    date_from = _parse_datetime_query_param(params.get("date_from"), "date_from")
    if date_from:
        queryset = queryset.filter(server_timestamp__gte=date_from)

    date_to = _parse_datetime_query_param(params.get("date_to"), "date_to")
    if date_to:
        queryset = queryset.filter(server_timestamp__lte=date_to)

    metadata_search = params.get("metadata_search")
    if metadata_search:
        queryset = queryset.annotate(metadata_text=Cast("metadata", TextField())).filter(
            metadata_text__icontains=metadata_search
        )

    return queryset


def _admin_export_filters(params) -> dict:
    keys = ("date_from", "date_to", "actor", "action_type", "action", "entity_type", "entity_id")
    return {key: params.get(key) for key in keys if params.get(key)}


def _parse_window_minutes(value: str | None) -> int:
    if not value:
        return 60

    try:
        minutes = int(value)
    except ValueError as exc:
        raise ValidationError({"window_minutes": "Use a whole number of minutes."}) from exc

    if minutes < 5 or minutes > 1440:
        raise ValidationError({"window_minutes": "Use a value between 5 and 1440 minutes."})

    return minutes


def _bid_event(bid: Bid) -> dict:
    return {
        "id": bid.id,
        "lot_id": bid.lot_id,
        "lot_title": bid.lot.title,
        "auction_id": bid.lot.auction_id,
        "auction_title": bid.lot.auction.title,
        "bidder_id": bid.bidder_id,
        "bidder_username": bid.bidder.username,
        "amount": str(bid.amount),
        "status": bid.status,
        "rejection_reason": bid.rejection_reason,
        "server_timestamp": bid.server_timestamp,
    }


def _suspicious_failures(recent_bids) -> list[dict]:
    failures = (
        recent_bids.filter(status=BidStatus.REJECTED)
        .values("bidder_id", "bidder__username", "rejection_reason")
        .annotate(count=Count("id"))
        .filter(count__gte=settings.BID_ANOMALY_REJECT_THRESHOLD)
        .order_by("-count", "bidder__username")[:10]
    )

    return [
        {
            "bidder_id": failure["bidder_id"],
            "bidder_username": failure["bidder__username"],
            "rejection_reason": failure["rejection_reason"],
            "count": failure["count"],
        }
        for failure in failures
    ]


def _suspicious_failure_count(recent_bids) -> int:
    return len(_suspicious_failures(recent_bids))
