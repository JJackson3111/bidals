from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    USER_REGISTERED = "user_registered", "User registered"
    AUCTION_CREATED = "auction_created", "Auction created"
    AUCTION_UPDATED = "auction_updated", "Auction updated"
    AUCTION_ENDED = "auction_ended", "Auction ended"
    AUCTION_CLOSE_RUN = "auction_close_run", "Auction close run"
    LOT_CREATED = "lot_created", "Lot created"
    LOT_UPDATED = "lot_updated", "Lot updated"
    BID_ACCEPTED = "bid_accepted", "Bid accepted"
    BID_REJECTED = "bid_rejected", "Bid rejected"
    BID_ANOMALY_DETECTED = "bid_anomaly_detected", "Bid anomaly detected"
    WINNER_CALCULATED = "winner_calculated", "Winner calculated"
    WINNER_OUTCOME_BACKFILLED = "winner_outcome_backfilled", "Winner outcome backfilled"
    OUTCOME_REPAIR_REQUESTED = "outcome_repair_requested", "Outcome repair requested"
    OUTCOME_REPAIR_APPROVED = "outcome_repair_approved", "Outcome repair approved"
    OUTCOME_REPAIR_INVALID_APPROVAL = "outcome_repair_invalid_approval", "Outcome repair invalid approval"
    OUTCOME_REPAIR_REJECTED = "outcome_repair_rejected", "Outcome repair rejected"
    OUTCOME_REPAIR_APPLIED = "outcome_repair_applied", "Outcome repair applied"
    OUTCOME_REPAIR_CANCELLED = "outcome_repair_cancelled", "Outcome repair cancelled"
    OUTCOME_REPAIR_COMMENT_CREATED = "outcome_repair_comment_created", "Outcome repair comment created"
    OUTCOME_REPAIR_AUDIT_VIEWED = "outcome_repair_audit_viewed", "Outcome repair audit viewed"
    ADMIN_ACTIVITY_EXPORTED = "admin_activity_exported", "Admin activity exported"
    DEPLOYMENT_CHECK_RUN = "deployment_check_run", "Deployment check run"
    STAGING_SEED_RUN = "staging_seed_run", "Staging seed run"
    BACKUP_VERIFICATION_RUN = "backup_verification_run", "Backup verification run"
    RELEASE_CHECK_RUN = "release_check_run", "Release check run"
    ALERT_TRIGGERED = "alert_triggered", "Alert triggered"
    NOTIFICATION_EVENT = "notification_event", "Notification event"
    NOTIFICATION_MARKED_READ = "notification_marked_read", "Notification marked read"
    NOTIFICATIONS_MARKED_READ = "notifications_marked_read", "Notifications marked read"
    JOB_FAILED = "job_failed", "Job failed"
    FULFILLMENT_CREATED = "fulfillment_created", "Fulfillment created"
    FULFILLMENT_STATUS_CHANGED = "fulfillment_status_changed", "Fulfillment status changed"
    FULFILLMENT_INVALID_TRANSITION = "fulfillment_invalid_transition", "Fulfillment invalid transition"
    FULFILLMENT_CONFIRMATION_NOTES_UPDATED = "fulfillment_confirmation_notes_updated", "Fulfillment confirmation notes updated"
    FULFILLMENT_SELLER_NOTES_UPDATED = "fulfillment_seller_notes_updated", "Fulfillment seller notes updated"
    FULFILLMENT_ADMIN_NOTES_UPDATED = "fulfillment_admin_notes_updated", "Fulfillment admin notes updated"
    FULFILLMENT_COMPLETED = "fulfillment_completed", "Fulfillment completed"
    FULFILLMENT_CANCELLED = "fulfillment_cancelled", "Fulfillment cancelled"
    FULFILLMENT_DISPUTED = "fulfillment_disputed", "Fulfillment disputed"
    ADMIN_ACTION = "admin_action", "Admin action"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    SKIPPED = "skipped", "Skipped"
    FAILED = "failed", "Failed"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=60, choices=AuditAction.choices)
    entity_type = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    server_timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-server_timestamp", "-id")
        indexes = [
            models.Index(fields=("entity_type", "entity_id"), name="audit_entity_idx"),
            models.Index(fields=("action", "-server_timestamp"), name="audit_action_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id}"


class OutboundNotification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="outbound_notifications",
        blank=True,
        null=True,
    )
    recipient_email = models.EmailField(blank=True)
    notification_type = models.CharField(max_length=80)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    related_entity_type = models.CharField(max_length=60)
    related_entity_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "created_at"), name="notification_status_idx"),
            models.Index(fields=("recipient", "read_at"), name="notification_read_idx"),
            models.Index(fields=("notification_type", "created_at"), name="notification_type_idx"),
            models.Index(fields=("related_entity_type", "related_entity_id"), name="notification_entity_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} to {self.recipient_email or 'unknown'}"
