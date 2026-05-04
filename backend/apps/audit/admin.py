from django.contrib import admin

from apps.audit.models import AuditLog, OutboundNotification


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "entity_type", "entity_id", "server_timestamp")
    list_filter = ("action", "entity_type", "server_timestamp")
    search_fields = ("actor__username", "actor__email", "entity_type", "entity_id")
    readonly_fields = ("actor", "action", "entity_type", "entity_id", "metadata", "server_timestamp")


@admin.register(OutboundNotification)
class OutboundNotificationAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "recipient_email", "status", "related_entity_type", "related_entity_id", "created_at", "sent_at")
    list_filter = ("status", "notification_type", "created_at", "sent_at")
    search_fields = ("recipient__username", "recipient__email", "recipient_email", "subject", "related_entity_id")
    readonly_fields = (
        "recipient",
        "recipient_email",
        "notification_type",
        "subject",
        "body",
        "status",
        "related_entity_type",
        "related_entity_id",
        "metadata",
        "created_at",
        "sent_at",
        "error_message",
    )
