from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
import logging

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.audit.services.alerts import send_alert
from apps.auctions.models import Bid, BidRejectionReason, BidStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BidAnomaly:
    anomaly_type: str
    anomaly_key: str
    count: int
    threshold: int
    metadata: dict
    audit_log_id: int | None = None


def detect_bid_anomalies(*, window_minutes: int = 60, now=None) -> list[BidAnomaly]:
    now = now or timezone.now()
    since = now - timedelta(minutes=window_minutes)
    anomalies = []
    anomalies.extend(_detect_rejected_bid_anomalies(since=since, now=now, window_minutes=window_minutes))
    anomalies.extend(_detect_rate_limit_anomalies(since=since, now=now, window_minutes=window_minutes))
    return anomalies


def _detect_rejected_bid_anomalies(*, since, now, window_minutes: int) -> list[BidAnomaly]:
    threshold = getattr(settings, "BID_ANOMALY_REJECT_THRESHOLD", 5)
    grouped_failures = (
        Bid.objects.filter(status=BidStatus.REJECTED, server_timestamp__gte=since)
        .values("bidder_id", "rejection_reason")
        .annotate(count=Count("id"))
        .filter(count__gte=threshold)
        .order_by("-count", "bidder_id", "rejection_reason")
    )

    anomalies = []
    for failure in grouped_failures:
        anomaly_key = f"rejected:{failure['bidder_id']}:{failure['rejection_reason']}"
        metadata = {
            "anomaly_type": "repeated_rejected_bids",
            "anomaly_key": anomaly_key,
            "bidder_id": failure["bidder_id"],
            "rejection_reason": failure["rejection_reason"],
            "count": failure["count"],
            "threshold": threshold,
            "window_minutes": window_minutes,
            "window_started_at": since.isoformat(),
            "window_ended_at": now.isoformat(),
        }
        anomalies.append(_record_anomaly(metadata=metadata, count=failure["count"], threshold=threshold))
    return [anomaly for anomaly in anomalies if anomaly is not None]


def _detect_rate_limit_anomalies(*, since, now, window_minutes: int) -> list[BidAnomaly]:
    threshold = getattr(settings, "BID_ANOMALY_RATE_LIMIT_THRESHOLD", 3)
    rate_limit_logs = AuditLog.objects.filter(
        action=AuditAction.BID_REJECTED,
        metadata__reason=BidRejectionReason.RATE_LIMITED,
        server_timestamp__gte=since,
    )
    counts = Counter(str(log.metadata.get("bidder_id") or "anonymous") for log in rate_limit_logs)

    anomalies = []
    for bidder_key, count in counts.items():
        if count < threshold:
            continue
        anomaly_key = f"rate_limited:{bidder_key}"
        bidder_id = None if bidder_key == "anonymous" else int(bidder_key)
        metadata = {
            "anomaly_type": "repeated_rate_limits",
            "anomaly_key": anomaly_key,
            "bidder_id": bidder_id,
            "count": count,
            "threshold": threshold,
            "window_minutes": window_minutes,
            "window_started_at": since.isoformat(),
            "window_ended_at": now.isoformat(),
        }
        anomalies.append(_record_anomaly(metadata=metadata, count=count, threshold=threshold))
    return [anomaly for anomaly in anomalies if anomaly is not None]


def _record_anomaly(*, metadata: dict, count: int, threshold: int) -> BidAnomaly | None:
    dedupe_since = timezone.now() - timedelta(minutes=15)
    if AuditLog.objects.filter(
        action=AuditAction.BID_ANOMALY_DETECTED,
        metadata__anomaly_key=metadata["anomaly_key"],
        server_timestamp__gte=dedupe_since,
    ).exists():
        return None

    audit = AuditLog.objects.create(
        actor=None,
        action=AuditAction.BID_ANOMALY_DETECTED,
        entity_type="bid_anomaly",
        entity_id=metadata["anomaly_key"],
        metadata=metadata,
    )
    logger.warning(
        "Bid anomaly detected",
        extra={
            "event": "bid_anomaly_detected",
            "anomaly_type": metadata["anomaly_type"],
            "anomaly_key": metadata["anomaly_key"],
            "count": count,
            "threshold": threshold,
            "bidder_id": metadata.get("bidder_id"),
            "rejection_reason": metadata.get("rejection_reason"),
        },
    )
    send_alert(
        event_type="bid_anomaly_detected",
        severity="warning",
        message="Bid anomaly threshold crossed.",
        metadata={**metadata, "audit_log_id": audit.id},
    )
    return BidAnomaly(
        anomaly_type=metadata["anomaly_type"],
        anomaly_key=metadata["anomaly_key"],
        count=count,
        threshold=threshold,
        metadata=metadata,
        audit_log_id=audit.id,
    )
