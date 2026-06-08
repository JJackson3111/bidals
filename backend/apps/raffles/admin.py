from django.contrib import admin

from apps.raffles.models import (
    RaffleCampaign,
    RaffleDraw,
    RafflePrize,
    RafflePurchase,
    RaffleTicket,
    RaffleWinner,
    SellerRaffleFeature,
)


@admin.register(SellerRaffleFeature)
class SellerRaffleFeatureAdmin(admin.ModelAdmin):
    list_display = ("seller", "plan_code", "raffles_enabled", "updated_at")
    list_filter = ("plan_code", "raffles_enabled")
    search_fields = ("seller__username", "seller__email")


class RafflePrizeInline(admin.TabularInline):
    model = RafflePrize
    extra = 0


@admin.register(RaffleCampaign)
class RaffleCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_by", "auction", "ticket_price", "max_tickets", "start_time", "end_time")
    list_filter = ("status",)
    search_fields = ("title", "created_by__username", "auction__title")
    inlines = (RafflePrizeInline,)


@admin.register(RafflePurchase)
class RafflePurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "buyer", "quantity", "gross_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("campaign__title", "buyer__username", "payment_reference")


@admin.register(RaffleTicket)
class RaffleTicketAdmin(admin.ModelAdmin):
    list_display = ("campaign", "ticket_number", "owner", "purchase", "status", "issued_at")
    list_filter = ("status",)
    search_fields = ("campaign__title", "owner__username", "ticket_number")


@admin.register(RaffleDraw)
class RaffleDrawAdmin(admin.ModelAdmin):
    list_display = ("campaign", "drawn_by", "drawn_at")
    search_fields = ("campaign__title", "drawn_by__username")


@admin.register(RaffleWinner)
class RaffleWinnerAdmin(admin.ModelAdmin):
    list_display = ("campaign", "prize", "ticket", "winner", "created_at")
    search_fields = ("campaign__title", "winner__username", "ticket__ticket_number")
