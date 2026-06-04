from django.contrib import admin

from apps.leads.models import LeadRequest


@admin.register(LeadRequest)
class LeadRequestAdmin(admin.ModelAdmin):
    list_display = ("organisation", "name", "email", "fundraising_focus", "source_page", "status", "created_at")
    list_filter = ("status", "source_page", "fundraising_focus", "created_at")
    search_fields = ("name", "email", "organisation", "message")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("status", "source_page", "fundraising_focus")}),
        ("Requester", {"fields": ("name", "email", "organisation")}),
        ("Message", {"fields": ("message",)}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def has_delete_permission(self, request, obj=None):
        return False
