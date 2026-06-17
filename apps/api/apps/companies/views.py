from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.onboarding import sync_company_approval_status
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import normalize_company_registration_number
from apps.companies.serializers import (
    CompanyAdminSerializer,
    CompanyDirectoryDetailSerializer,
    CompanyProfileSerializer,
    CompanyProfileSubmissionSerializer,
    CompanyVerificationSerializer,
)
from apps.search.services import apply_company_recommendations
from apps.companies.services import ensure_company_profile, notify_company_verification_admins
from apps.companies.verification import verify_company_profile_or_raise
from apps.common.permissions import IsAdminUserRole, IsCompanyUser, IsCorperUser
from apps.subscriptions.services import enforce_browse_access


def _set_company_unsubmitted(company: CompanyProfile):
    fields_to_update = ["updated_at"]
    if company.verification_status != CompanyProfile.VerificationStatus.UNSUBMITTED:
        company.verification_status = CompanyProfile.VerificationStatus.UNSUBMITTED
        fields_to_update.append("verification_status")
    if company.approval_status != CompanyProfile.ApprovalStatus.UNSUBMITTED:
        company.approval_status = CompanyProfile.ApprovalStatus.UNSUBMITTED
        fields_to_update.append("approval_status")
    if len(fields_to_update) > 1:
        company.save(update_fields=fields_to_update)


def _verify_company_or_reject(company: CompanyProfile):
    try:
        verify_company_profile_or_raise(company)
    except ValidationError:
        fields_to_update = ["updated_at"]
        if company.verification_status != CompanyProfile.VerificationStatus.REJECTED:
            company.verification_status = CompanyProfile.VerificationStatus.REJECTED
            fields_to_update.append("verification_status")
        if company.approval_status != CompanyProfile.ApprovalStatus.UNSUBMITTED:
            company.approval_status = CompanyProfile.ApprovalStatus.UNSUBMITTED
            fields_to_update.append("approval_status")
        if len(fields_to_update) > 1:
            company.save(update_fields=fields_to_update)
        raise
    if company.verification_status != CompanyProfile.VerificationStatus.VERIFIED:
        company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        company.save(update_fields=["verification_status", "updated_at"])


def _sync_company_approval_status(company: CompanyProfile):
    previous_approval_status = company.approval_status
    sync_company_approval_status(company)
    company.refresh_from_db()
    if (
        previous_approval_status != CompanyProfile.ApprovalStatus.PENDING
        and company.approval_status == CompanyProfile.ApprovalStatus.PENDING
    ):
        notify_company_verification_admins(company=company)


class CompanyVerificationAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyVerificationSerializer
    permission_classes = [IsCompanyUser]

    verification_fields = {
        "company_name",
        "company_registration_number",
        "company_registration_date",
    }

    def get_object(self):
        return ensure_company_profile(self.request.user)

    def update(self, request, *args, **kwargs):
        company = self.get_object()
        previous_values = {
            field_name: getattr(company, field_name, None)
            for field_name in self.verification_fields
        }

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        company.refresh_from_db()
        verification_fields_changed = any(
            previous_values[field_name] != getattr(company, field_name, None)
            for field_name in self.verification_fields
        )

        if verification_fields_changed:
            if company.terms_accepted and company.verification_fields_complete:
                _verify_company_or_reject(company)
            else:
                _set_company_unsubmitted(company)

        _sync_company_approval_status(company)
        return Response(self.get_serializer(company).data)


class MyCompanyProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsCompanyUser]
    verified_editable_fields = {
        "desired_corper_description",
        "desired_qualification",
        "desired_age_range",
        "desired_field_of_study",
        "desired_university",
        "desired_posting_states",
        "desired_skills",
        "desired_experience",
        "company_function",
        "company_image",
    }

    def get_object(self):
        return ensure_company_profile(self.request.user)

    def is_verified_edit_mode(self):
        return self.request.query_params.get("edit") == "1"

    def update(self, request, *args, **kwargs):
        company = self.get_object()
        previous_verification_values = {
            "company_name": company.company_name,
            "company_registration_number": normalize_company_registration_number(
                company.company_registration_number
            ),
            "company_registration_date": company.company_registration_date,
        }
        if (
            company.approval_status == CompanyProfile.ApprovalStatus.APPROVED
            and not self.is_verified_edit_mode()
        ):
            disallowed_fields = set(request.data.keys()) - self.verified_editable_fields
            if disallowed_fields:
                return Response(
                    {
                        "detail": (
                            "Only the profile preferences and company image can be updated here. "
                            "Contact admin/support team to change the remaining company fields."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        company.refresh_from_db()
        verification_fields_changed = (
            company.company_name != previous_verification_values["company_name"]
            or normalize_company_registration_number(company.company_registration_number)
            != previous_verification_values["company_registration_number"]
            or company.company_registration_date != previous_verification_values["company_registration_date"]
        )
        if (
            company.approval_status == CompanyProfile.ApprovalStatus.APPROVED
            and not verification_fields_changed
        ):
            return Response(self.get_serializer(company).data)

        if verification_fields_changed:
            if company.terms_accepted and company.verification_fields_complete:
                _verify_company_or_reject(company)
            else:
                _set_company_unsubmitted(company)
        elif not company.verification_fields_complete:
            _set_company_unsubmitted(company)

        _sync_company_approval_status(company)

        return Response(self.get_serializer(company).data)


class CompanyAdminListAPIView(generics.ListAPIView):
    serializer_class = CompanyAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = CompanyProfile.objects.select_related("user").all()
    search_fields = [
        "company_name",
        "company_sector",
        "company_function",
        "desired_field_of_study",
        "desired_university",
        "desired_posting_states",
        "contact_email",
        "user__email",
    ]
    ordering_fields = ["created_at", "company_name"]


class CompanyDirectoryDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CompanyDirectoryDetailSerializer
    permission_classes = [IsCorperUser | IsAdminUserRole]
    queryset = CompanyProfile.objects.select_related("user").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "corper":
            enforce_browse_access(user=self.request.user)
            queryset = queryset.filter(
                verification_status=CompanyProfile.VerificationStatus.VERIFIED,
            ).filter(
                CompanyProfile.directory_visibility_q()
            )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        company = self.get_object()
        company = apply_company_recommendations(viewer=request.user, companies=[company])[0]
        serializer = self.get_serializer(company)
        return Response(serializer.data)


class CompanyAdminDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = CompanyProfile.objects.select_related("user").all()


class CompanyProfileSubmitAPIView(APIView):
    permission_classes = [IsCompanyUser]

    def post(self, request, *args, **kwargs):
        company = ensure_company_profile(request.user)
        if not company.verification_fields_complete:
            return Response(
                {
                    "detail": (
                        "Complete the company verification fields before submitting your legal documents."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CompanyProfileSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _verify_company_or_reject(company)
        serializer.save(profile=company)

        company.refresh_from_db()
        _sync_company_approval_status(company)

        return Response(CompanyProfileSerializer(company, context={"request": request}).data)
