from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from rest_framework_simplejwt.token_blacklist.admin import (
    OutstandingTokenAdmin as SimpleJWTOutstandingTokenAdmin,
)
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.accounts.models import CompanyUser, CorperUser, EmailDomainRule, EmailOTP, PendingSignup


class RoleScopedUserAdmin(BaseUserAdmin):
    user_role: str
    ordering = ("email",)
    list_display = ("email", "email_verified", "is_staff", "is_active", "created_at")
    list_filter = ("email_verified", "is_staff", "is_active")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Status", {"fields": ("role", "email_verified", "is_active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "role", "password1", "password2", "email_verified", "is_staff", "is_superuser"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(role=self.user_role)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "role":
            kwargs["choices"] = [choice for choice in db_field.choices if choice[0] == self.user_role]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial["role"] = self.user_role
        return initial

    def save_model(self, request, obj, form, change):
        obj.role = self.user_role
        super().save_model(request, obj, form, change)


@admin.register(CompanyUser)
class CompanyUserAdmin(RoleScopedUserAdmin):
    user_role = "company"


@admin.register(CorperUser)
class CorperUserAdmin(RoleScopedUserAdmin):
    user_role = "corper"


try:
    admin.site.unregister(OutstandingToken)
except NotRegistered:
    pass


@admin.register(OutstandingToken)
class OutstandingTokenAdmin(SimpleJWTOutstandingTokenAdmin):
    actions = ["delete_selected"]

    def has_delete_permission(self, request, obj=None) -> bool:
        return super(SimpleJWTOutstandingTokenAdmin, self).has_delete_permission(request, obj)


@admin.register(PendingSignup)
class PendingSignupAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "role",
        "company_name",
        "company_registration_number",
        "created_at",
        "updated_at",
    )
    search_fields = ("email", "company_name", "company_registration_number")
    list_filter = ("role",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "expires_at", "attempt_count", "verified_at", "consumed_at")
    search_fields = ("email",)
    list_filter = ("purpose", "verified_at", "consumed_at")
    readonly_fields = ("created_at", "updated_at", "verified_at", "consumed_at")


@admin.register(EmailDomainRule)
class EmailDomainRuleAdmin(admin.ModelAdmin):
    list_display = ("domain", "rule_type", "note", "created_at")
    search_fields = ("domain", "note")
    list_filter = ("rule_type",)
    readonly_fields = ("created_at", "updated_at")
