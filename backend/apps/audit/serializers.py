from rest_framework import serializers

from apps.audit.models import AuditLog, OutboundNotification
from apps.audit.safety import sanitize_metadata


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_username",
            "action",
            "entity_type",
            "entity_id",
            "metadata",
            "server_timestamp",
        )
        read_only_fields = fields


class SafeAuditLogSerializer(AuditLogSerializer):
    metadata = serializers.SerializerMethodField()

    def get_metadata(self, obj):
        return sanitize_metadata(obj.metadata)


class OutboundNotificationSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(source="recipient.username", read_only=True, allow_null=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = OutboundNotification
        fields = (
            "id",
            "recipient",
            "recipient_username",
            "recipient_email",
            "notification_type",
            "subject",
            "status",
            "related_entity_type",
            "related_entity_id",
            "metadata",
            "created_at",
            "sent_at",
            "read_at",
            "is_read",
            "error_message",
        )
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.read_at is not None


class AccountNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = OutboundNotification
        fields = (
            "id",
            "notification_type",
            "subject",
            "body",
            "status",
            "related_entity_type",
            "related_entity_id",
            "created_at",
            "sent_at",
            "read_at",
            "is_read",
        )
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.read_at is not None
