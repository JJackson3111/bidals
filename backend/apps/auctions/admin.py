from django.contrib import admin

from apps.auctions.models import Auction, Bid, FulfillmentRecord, Lot, LotImage, OutcomeRepairComment, OutcomeRepairRequest


class LotInline(admin.TabularInline):
    model = Lot
    extra = 0
    fields = ("title", "status", "starting_price", "current_price", "bid_increment", "winner_status")
    readonly_fields = ("current_price", "winner_status")


class LotImageInline(admin.TabularInline):
    model = LotImage
    extra = 0
    fields = ("image", "alt_text", "sort_order", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "start_time", "end_time", "created_by")
    list_filter = ("status", "start_time", "end_time")
    search_fields = ("title", "description")
    inlines = (LotInline,)


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("title", "auction", "status", "starting_price", "current_price", "winner_status", "winner")
    list_filter = ("status", "winner_status", "auction")
    search_fields = ("title", "description")
    readonly_fields = ("current_price", "winner", "winning_bid", "winner_status", "winner_calculated_at")
    inlines = (LotImageInline,)


@admin.register(LotImage)
class LotImageAdmin(admin.ModelAdmin):
    list_display = ("lot", "alt_text", "sort_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("lot__title", "alt_text")


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("lot", "bidder", "amount", "status", "server_timestamp")
    list_filter = ("status", "rejection_reason", "server_timestamp")
    search_fields = ("lot__title", "bidder__username", "bidder__email")
    readonly_fields = ("lot", "bidder", "amount", "status", "rejection_reason", "server_timestamp", "created_at")


@admin.register(FulfillmentRecord)
class FulfillmentRecordAdmin(admin.ModelAdmin):
    list_display = ("lot", "auction", "winner", "status", "last_follow_up_at", "completed_at", "updated_at")
    list_filter = ("status", "last_follow_up_at", "completed_at", "updated_at")
    search_fields = ("lot__title", "auction__title", "winner__username", "winner__email")
    readonly_fields = ("lot", "auction", "winning_bid", "winner", "created_at", "updated_at")


@admin.register(OutcomeRepairRequest)
class OutcomeRepairRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "lot", "status", "requested_winner", "requested_by", "reviewed_by", "applied_by", "created_at")
    list_filter = ("status", "created_at", "applied_at")
    search_fields = ("lot__title", "auction__title", "requested_winner__username", "requested_by__username", "reason")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "applied_at")


@admin.register(OutcomeRepairComment)
class OutcomeRepairCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "repair_request", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("repair_request__lot__title", "author__username", "comment_text")
    readonly_fields = ("repair_request", "author", "comment_text", "metadata", "created_at", "updated_at")
