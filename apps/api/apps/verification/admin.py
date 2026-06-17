from django.contrib import admin, messages
from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils.html import format_html

from apps.verification.models import CorperVerification, VerificationAttempt


class VerificationAttemptInline(admin.TabularInline):
    model = VerificationAttempt
    extra = 0
    can_delete = False
    fields = (
        "verification_type",
        "status",
        "submitted_value_masked",
        "submitted_document",
        "reviewed_by",
        "review_note",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Document")
    def submitted_document(self, obj):
        metadata = obj.metadata or {}
        document_path = str(metadata.get("document_path", "")).strip()
        if not document_path:
            return "No document"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">View submitted document</a>',
            document_path,
        )


@admin.register(CorperVerification)
class CorperVerificationAdmin(admin.ModelAdmin):
    actions = ("delete_selected_verifications",)
    list_display = (
        "user_email",
        "verification_status",
        "biodata_verification_status",
        "nin_verification_status",
        "nysc_callup_verification_status",
        "nysc_state_code_verification_status",
        "full_name",
        "university_matriculation_number",
        "masked_nin_number",
        "masked_callup_number",
        "masked_state_code",
        "updated_at",
    )
    search_fields = ("full_name", "user__email", "nin_last4", "nysc_callup_number", "nysc_state_code")
    list_filter = (
        "verification_status",
        "biodata_verification_status",
        "nin_verification_status",
        "nysc_callup_verification_status",
        "nysc_state_code_verification_status",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "user",
        "review_full_name",
        "review_date_of_birth",
        "review_university_matriculation_number",
        "nin_number",
        "masked_nin_number",
        "nysc_callup_number",
        "masked_callup_number",
        "view_nysc_callup_document",
        "nysc_state_code",
        "masked_state_code",
        "view_nysc_state_code_document",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Corper", {"fields": ("user",)}),
        (
            "Document Review",
            {
                "fields": (
                    "review_full_name",
                    "review_date_of_birth",
                    "review_university_matriculation_number",
                    "biodata_verification_status",
                    "nin_number",
                    "masked_nin_number",
                    "nin_verification_status",
                    "nysc_callup_number",
                    "masked_callup_number",
                    "view_nysc_callup_document",
                    "nysc_callup_verification_status",
                    "nysc_state_code",
                    "masked_state_code",
                    "view_nysc_state_code_document",
                    "nysc_state_code_verification_status",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = (VerificationAttemptInline,)
    list_select_related = ("user",)
    list_display_links = ("user_email",)

    @admin.display(ordering="user__email", description="User/Email")
    def user_email(self, obj):
        return obj.user.email

    def _latest_biodata_attempt(self, obj):
        attempts = getattr(obj, "_prefetched_objects_cache", {}).get("verification_attempts")
        if attempts is None:
            attempts = obj.verification_attempts.all()
        for attempt in attempts:
            if attempt.verification_type == VerificationAttempt.VerificationType.BIODATA and attempt.metadata:
                return attempt
        return None

    def _review_biodata_value(self, obj, field_name):
        attempt = self._latest_biodata_attempt(obj)
        if attempt:
            metadata_value = str((attempt.metadata or {}).get(field_name, "")).strip()
            if metadata_value:
                if field_name == "date_of_birth":
                    return parse_date(metadata_value) or metadata_value
                return metadata_value
        return getattr(obj, field_name, None)

    @admin.display(description="Full name")
    def review_full_name(self, obj):
        return self._review_biodata_value(obj, "full_name")

    @admin.display(description="Date of birth")
    def review_date_of_birth(self, obj):
        return self._review_biodata_value(obj, "date_of_birth")

    @admin.display(description="University matriculation number")
    def review_university_matriculation_number(self, obj):
        return self._review_biodata_value(obj, "university_matriculation_number")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user").prefetch_related("verification_attempts")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Call-up document")
    def view_nysc_callup_document(self, obj):
        if not obj.nysc_callup_document:
            return "No document uploaded"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">View uploaded document</a>',
            obj.nysc_callup_document.url,
        )

    @admin.display(description="State code document")
    def view_nysc_state_code_document(self, obj):
        if not obj.nysc_state_code_document:
            return "No document uploaded"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">View uploaded document</a>',
            obj.nysc_state_code_document.url,
        )

    @admin.action(description="Delete selected verifications")
    def delete_selected_verifications(self, request, queryset):
        verification_ids = list(queryset.values_list("pk", flat=True))
        selected_count = len(verification_ids)
        deleted_attempts = VerificationAttempt.objects.filter(corper_id__in=verification_ids).count()

        with transaction.atomic():
            CorperVerification.objects.filter(pk__in=verification_ids).delete()

        self.message_user(
            request,
            (
                f"Deleted {selected_count} verification profile(s) "
                f"and removed {deleted_attempts} verification submission(s)."
            ),
            level=messages.SUCCESS,
        )
