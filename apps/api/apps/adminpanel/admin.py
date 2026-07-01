from django.contrib import admin

from apps.adminpanel.models import AdminRegistrationRequest, PlatformOption


@admin.register(AdminRegistrationRequest)
class AdminRegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "reviewed_by_email", "notification_sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at", "notification_sent_at", "reviewed_at", "reviewed_by")
    fieldsets = (
        (None, {"fields": ("email", "status")}),
        ("Review", {"fields": ("reviewed_by", "reviewed_at", "notification_sent_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None

    reviewed_by_email.short_description = "Reviewed by"
    reviewed_by_email.admin_order_field = "reviewed_by__email"


@admin.register(PlatformOption)
class PlatformOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("label", "value")
    readonly_fields = ("created_at", "updated_at")
