from django.contrib import admin

from apps.audit.models import AuditAction, AuditLog
from apps.audit.safety import sanitize_metadata
from apps.auctions.models import (
    Auction,
    Bid,
    FulfillmentRecord,
    Lot,
    LotImage,
    OutcomeRepairComment,
    OutcomeRepairRequest,
)


SENSITIVE_AUCTION_FIELDS = ("status", "start_time", "end_time", "created_by")
SENSITIVE_LOT_FIELDS = (
    "auction",
    "status",
    "starting_price",
    "reserve_price",
    "bid_increment",
    "current_price",
    "winner",
    "winning_bid",
    "winner_status",
    "winner_calculated_at",
)
INLINE_SENSITIVE_LOT_FIELDS = (
    "status",
    "starting_price",
    "bid_increment",
    "current_price",
    "winner_status",
)


def _dedupe_fields(*field_groups):
    fields = []
    for group in field_groups:
        for field in group:
            if field not in fields:
                fields.append(field)
    return tuple(fields)


def _model_field_names(model):
    return tuple(field.name for field in model._meta.fields)


def _admin_actor(request):
    user = getattr(request, "user", None)
    return user if getattr(user, "is_authenticated", False) else None


def _audit_admin_change(*, request, action, entity_type, entity_id, metadata):
    AuditLog.objects.create(
        actor=_admin_actor(request),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        metadata=sanitize_metadata(
            {
                "source": "django_admin",
                "admin_user_id": getattr(_admin_actor(request), "id", None),
                **metadata,
            }
        ),
    )


class NoDeleteAdminMixin:
    def has_delete_permission(self, request, obj=None):
        return False


class LotInline(admin.TabularInline):
    model = Lot
    extra = 0
    fields = (
        "title",
        "status",
        "starting_price",
        "current_price",
        "bid_increment",
        "winner_status",
    )
    readonly_fields = ("current_price", "winner_status")
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly_fields
        return _dedupe_fields(readonly_fields, INLINE_SENSITIVE_LOT_FIELDS)


class LotImageInline(admin.TabularInline):
    model = LotImage
    extra = 0
    fields = ("image", "alt_text", "sort_order", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False


@admin.register(Auction)
class AuctionAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("title", "status", "start_time", "end_time", "created_by")
    list_filter = ("status", "start_time", "end_time")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = (LotInline,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly_fields
        return _dedupe_fields(readonly_fields, SENSITIVE_AUCTION_FIELDS)

    def save_model(self, request, obj, form, change):
        changed_fields = sorted(getattr(form, "changed_data", []) or [])
        super().save_model(request, obj, form, change)
        if changed_fields:
            _audit_admin_change(
                request=request,
                action=AuditAction.AUCTION_UPDATED if change else AuditAction.AUCTION_CREATED,
                entity_type="auction",
                entity_id=obj.id,
                metadata={
                    "auction_id": obj.id,
                    "changed_fields": changed_fields,
                    "status": obj.status,
                },
            )


@admin.register(Lot)
class LotAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("title", "auction", "status", "starting_price", "current_price", "winner_status", "winner")
    list_filter = ("status", "winner_status", "auction")
    search_fields = ("title", "description")
    readonly_fields = ("current_price", "winner", "winning_bid", "winner_status", "winner_calculated_at")
    inlines = (LotImageInline,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly_fields
        return _dedupe_fields(readonly_fields, SENSITIVE_LOT_FIELDS)

    def save_model(self, request, obj, form, change):
        changed_fields = sorted(getattr(form, "changed_data", []) or [])
        super().save_model(request, obj, form, change)
        if changed_fields:
            _audit_admin_change(
                request=request,
                action=AuditAction.LOT_UPDATED if change else AuditAction.LOT_CREATED,
                entity_type="lot",
                entity_id=obj.id,
                metadata={
                    "lot_id": obj.id,
                    "auction_id": obj.auction_id,
                    "changed_fields": changed_fields,
                    "status": obj.status,
                    "winner_status": obj.winner_status,
                },
            )


@admin.register(LotImage)
class LotImageAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("lot", "alt_text", "sort_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("lot__title", "alt_text")
    readonly_fields = ("created_at",)


@admin.register(Bid)
class BidAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("lot", "bidder", "amount", "status", "server_timestamp")
    list_filter = ("status", "rejection_reason", "server_timestamp")
    search_fields = ("lot__title", "bidder__username", "bidder__email")
    readonly_fields = ("lot", "bidder", "amount", "status", "rejection_reason", "server_timestamp", "created_at")


@admin.register(FulfillmentRecord)
class FulfillmentRecordAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("lot", "auction", "winner", "status", "last_follow_up_at", "completed_at", "updated_at")
    list_filter = ("status", "last_follow_up_at", "completed_at", "updated_at")
    search_fields = ("lot__title", "auction__title", "winner__username", "winner__email")
    readonly_fields = ("lot", "auction", "winning_bid", "winner", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        changed_fields = sorted(getattr(form, "changed_data", []) or [])
        super().save_model(request, obj, form, change)
        if changed_fields:
            _audit_admin_change(
                request=request,
                action=AuditAction.ADMIN_ACTION,
                entity_type="fulfillment",
                entity_id=obj.id,
                metadata={
                    "admin_action": "fulfillment_updated" if change else "fulfillment_created",
                    "fulfillment_id": obj.id,
                    "lot_id": obj.lot_id,
                    "auction_id": obj.auction_id,
                    "changed_fields": changed_fields,
                    "status": obj.status,
                },
            )


@admin.register(OutcomeRepairRequest)
class OutcomeRepairRequestAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "lot",
        "status",
        "requested_winner",
        "requested_by",
        "reviewed_by",
        "applied_by",
        "created_at",
    )
    list_filter = ("status", "created_at", "applied_at")
    search_fields = ("lot__title", "auction__title", "requested_winner__username", "requested_by__username", "reason")
    readonly_fields = _model_field_names(OutcomeRepairRequest)

    def has_add_permission(self, request):
        return False


@admin.register(OutcomeRepairComment)
class OutcomeRepairCommentAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("id", "repair_request", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("repair_request__lot__title", "author__username", "comment_text")
    readonly_fields = _model_field_names(OutcomeRepairComment)

    def has_add_permission(self, request):
        return False
