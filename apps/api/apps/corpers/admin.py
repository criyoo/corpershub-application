from django import forms
from django.contrib import admin
from django.utils.html import format_html

from apps.accounts.onboarding import maybe_send_corper_approval_welcome_email
from apps.corpers.models import CorperProfile


def extract_nysc_service_year(callup_number: str | None) -> str:
    parts = (callup_number or "").strip().split("/")
    if len(parts) < 3:
        return ""

    service_year = parts[2].strip()
    if len(service_year) != 4 or not service_year.isdigit():
        return ""
    return service_year


class CorperProfileAdminForm(forms.ModelForm):
    nysc_service_year = forms.CharField(required=False, max_length=4, label="NYSC service year")

    class Meta:
        model = CorperProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nysc_service_year"].initial = extract_nysc_service_year(
            getattr(self.instance, "nysc_callup_number", "")
        )
        if "approval_status" in self.fields:
            self.fields["approval_status"].required = False

    def clean_nysc_service_year(self):
        service_year = (self.cleaned_data.get("nysc_service_year") or "").strip()
        if service_year and (len(service_year) != 4 or not service_year.isdigit()):
            raise forms.ValidationError("Enter a 4-digit NYSC service year.")
        return service_year

    def clean(self):
        cleaned_data = super().clean()
        if "nysc_service_year" not in self.changed_data:
            return cleaned_data

        service_year = cleaned_data.get("nysc_service_year", "")
        if not service_year:
            return cleaned_data

        callup_number = (cleaned_data.get("nysc_callup_number") or "").strip()
        if not callup_number:
            self.add_error(
                "nysc_callup_number",
                "Enter an NYSC callup number before editing the service year.",
            )
            return cleaned_data

        parts = [part.strip() for part in callup_number.split("/")]
        if len(parts) < 3:
            self.add_error(
                "nysc_callup_number",
                "Use the NYSC callup number format before editing the service year.",
            )
            return cleaned_data

        parts[2] = service_year
        cleaned_data["nysc_callup_number"] = "/".join(parts)
        return cleaned_data


@admin.register(CorperProfile)
class CorperProfileAdmin(admin.ModelAdmin):
    form = CorperProfileAdminForm
    list_display = (
        "full_name",
        "user",
        "university",
        "field_of_study",
        "batch",
        "stream",
        "university_matriculation_number",
        "graduation_year",
        "posting_location_state",
        "approval_status",
        "is_complete",
        "created_at",
        "updated_at",
    )
    search_fields = ("full_name", "user__email", "university", "field_of_study", "skill")
    list_filter = ("posting_location_state", "graduation_year", "approval_status")
    fieldsets = (
        (
            "Profile",
            {
                "fields": (
                    "user",
                    "full_name",
                    "date_of_birth",
                    "gender",
                    "posting_location_state",
                    "batch",
                    "stream",
                    "field_of_study",
                    "degree",
                    "university",
                    "university_matriculation_number",
                    "graduation_year",
                    "profile_photo",
                    "mobile_number",
                    "skill",
                    "technical_skills",
                    "soft_skills",
                    "languages_spoken",
                    "available_date",
                    "bio",
                    "approval_status",
                    "is_complete",
                )
            },
        ),
        (
            "Preferred organisation",
            {
                "fields": (
                    "preferred_sector",
                    "preferred_organization_type",
                    "preferred_placement_type",
                    "preferred_monthly_allowance",
                    "preferred_organization_experience",
                )
            },
        ),
        (
            "Legal agreements",
            {
                "fields": (
                    "terms_of_agreement_accepted_at",
                    "terms_of_use_accepted_at",
                    "legal_acceptances",
                )
            },
        ),
        (
            "Verification center fields",
            {
                "fields": (
                    "nin_number",
                    "masked_nin_number",
                    "nysc_callup_number",
                    "nysc_callup_document",
                    "view_nysc_callup_document",
                    "nysc_service_year",
                    "masked_callup_number",
                    "nysc_state_code",
                    "nysc_state_code_document",
                    "view_nysc_state_code_document",
                    "masked_state_code",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = (
        "is_complete",
        "masked_nin_number",
        "masked_callup_number",
        "masked_state_code",
        "terms_of_agreement_accepted_at",
        "terms_of_use_accepted_at",
        "legal_acceptances",
        "view_nysc_callup_document",
        "view_nysc_state_code_document",
        "created_at",
        "updated_at",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["posting_location_state"].label = "Posting state"
        form.base_fields["skill"].label = "Primary skill"
        form.base_fields["approval_status"].help_text = (
            "Use this dropdown to approve or reject the completed corper profile after review."
        )
        return form

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = (
                CorperProfile.objects.filter(pk=obj.pk)
                .values_list("approval_status", flat=True)
                .first()
            )
        super().save_model(request, obj, form, change)
        maybe_send_corper_approval_welcome_email(obj, previous_status=previous_status)

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
