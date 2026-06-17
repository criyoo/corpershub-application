from django.contrib import admin

from apps.accounts.onboarding import maybe_send_company_approval_welcome_email
from apps.companies.models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "company_registration_number",
        "tax_identification_number",
        "user",
        "company_sector",
        "company_function",
        "desired_field_of_study",
        "desired_university",
        "desired_posting_states",
        "company_location_state",
        "verification_status",
        "approval_status",
        "is_complete",
        "created_at",
    )
    search_fields = (
        "company_name",
        "company_registration_number",
        "tax_identification_number",
        "user__email",
        "company_sector",
        "company_function",
        "desired_field_of_study",
        "desired_university",
        "desired_posting_states",
    )
    list_filter = ("verification_status", "approval_status", "company_sector", "company_location_state")
    fieldsets = (
        (
            "Company profile",
            {
                "fields": (
                    "user",
                    "company_name",
                    "company_registration_number",
                    "company_registration_date",
                    "tax_identification_number",
                    "company_image",
                    "company_sector",
                    "organization_type",
                    "staff_count_range",
                    "ppa_capacity",
                    "office_location_count",
                    "company_function",
                    "placement_type",
                    "monthly_allowance_offered",
                    "accommodation_provided",
                    "ppa_support",
                    "company_location_state",
                    "preferred_deployment_states",
                    "company_location_city",
                    "company_address",
                    "head_office_address",
                    "company_website",
                    "contact_name",
                    "contact_email",
                    "contact_phone",
                    "directors_name",
                    "director_phone_number",
                )
            },
        ),
        ("Company summary", {"fields": ("desired_corper_description",)}),
        (
            "Desired corper profile",
            {
                "fields": (
                    "desired_qualification",
                    "desired_age_range",
                    "desired_field_of_study",
                    "desired_university",
                    "desired_posting_states",
                    "desired_skills",
                    "desired_experience",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "verification_status",
                    "approval_status",
                    "is_complete",
                    "terms_of_agreement_accepted_at",
                    "terms_of_use_accepted_at",
                    "legal_acceptances",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = (
        "is_complete",
        "terms_of_agreement_accepted_at",
        "terms_of_use_accepted_at",
        "legal_acceptances",
        "created_at",
        "updated_at",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["desired_corper_description"].label = "Company summary"
        form.base_fields["approval_status"].required = False
        form.base_fields["company_registration_number"].help_text = (
            "Review this registration number manually before marking the company as verified."
        )
        form.base_fields["tax_identification_number"].help_text = (
            "Review this tax identification number manually before marking the company as verified."
        )
        form.base_fields["verification_status"].help_text = (
            "This reflects the automatic CAC verification result for the company verification details."
        )
        form.base_fields["approval_status"].help_text = (
            "Use this dropdown to approve or reject the completed company profile after review."
        )
        return form

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = (
                CompanyProfile.objects.filter(pk=obj.pk)
                .values_list("approval_status", flat=True)
                .first()
            )
        super().save_model(request, obj, form, change)
        maybe_send_company_approval_welcome_email(obj, previous_status=previous_status)
