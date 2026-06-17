from apps.accounts.models import User
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.onboarding import sync_corper_approval_status
from apps.common.permissions import IsAdminUserRole, IsCompanyUser, IsCorperUser
from apps.search.services import apply_corper_recommendations
from apps.corpers.models import CorperProfile
from apps.corpers.serializers import (
    CorperAdminSerializer,
    CorperAdminVerificationSerializer,
    CorperDirectorySerializer,
    CorperDirectoryDetailSerializer,
    CorperProfileSerializer,
    CorperProfileSubmissionSerializer,
)
from apps.corpers.services import ensure_corper_profile


class MyCorperProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CorperProfileSerializer
    permission_classes = [IsCorperUser]
    verified_editable_fields = {
        "gender",
        "posting_location_state",
        "technical_skills",
        "soft_skills",
        "languages_spoken",
        "available_date",
        "bio",
        "profile_photo",
        "preferred_sector",
        "preferred_organization_type",
        "preferred_placement_type",
        "preferred_monthly_allowance",
        "preferred_organization_experience",
    }

    def get_object(self):
        return ensure_corper_profile(self.request.user)

    def update(self, request, *args, **kwargs):
        corper = self.get_object()
        restricted_verification_fields = {
            "full_name",
            "first_name",
            "middle_name",
            "surname",
            "date_of_birth",
            "state_of_origin",
            "country_of_birth",
            "university_matriculation_number",
            "nin_number",
            "nysc_callup_number",
            "nysc_state_code",
        }
        if restricted_verification_fields.intersection(request.data.keys()):
            return Response(
                {
                    "detail": (
                        "Use the verification center to submit your verified identity details, NIN, "
                        "NYSC call-up number, and NYSC state code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not corper.documents_verified:
            return Response(
                {
                    "detail": (
                        "Complete biodata, NIN, NYSC call-up, and NYSC state code verification "
                        "before editing your profile."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not corper.terms_accepted:
            return Response(
                {
                    "detail": (
                        "Accept every required legal document before editing your corper profile."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if corper.profile_locked:
            disallowed_fields = set(request.data.keys()) - self.verified_editable_fields
            if disallowed_fields:
                return Response(
                    {
                        "detail": (
                            "Only gender, posting state, technical skills, soft skills, languages spoken, "
                            "available date, bio, profile photo, and preferred organisation fields can be "
                            "updated here. Contact admin/support team to change the remaining profile fields."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(corper, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        corper.refresh_from_db()
        sync_corper_approval_status(corper)
        return Response(self.get_serializer(corper).data)


class CorperDirectoryDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CorperDirectoryDetailSerializer
    permission_classes = [IsCompanyUser | IsAdminUserRole]
    queryset = CorperProfile.objects.select_related("user").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "company":
            queryset = queryset.filter(CorperProfile.directory_visibility_q())
        return queryset

    def retrieve(self, request, *args, **kwargs):
        corper = self.get_object()
        corper = apply_corper_recommendations(viewer=request.user, corpers=[corper])[0]
        serializer = self.get_serializer(corper)
        return Response(serializer.data)


class CorperAdminListAPIView(generics.ListAPIView):
    serializer_class = CorperAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = CorperProfile.objects.select_related("user").all()
    search_fields = ["full_name", "university", "field_of_study", "user__email", "skill"]
    ordering_fields = ["created_at", "graduation_year", "full_name"]


class CorperAdminDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CorperAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = CorperProfile.objects.select_related("user").all()


class CorperAdminVerificationListAPIView(generics.ListAPIView):
    serializer_class = CorperAdminVerificationSerializer
    permission_classes = [IsAdminUserRole]
    queryset = User.objects.filter(role=User.Role.CORPER).select_related("corper_profile")
    search_fields = ["email", "corper_profile__full_name"]
    ordering_fields = ["created_at", "email"]


class CorperAdminVerificationDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CorperAdminVerificationSerializer
    permission_classes = [IsAdminUserRole]
    queryset = User.objects.filter(role=User.Role.CORPER).select_related("corper_profile")


class CorperProfileSubmitAPIView(APIView):
    permission_classes = [IsCorperUser]

    def post(self, request, *args, **kwargs):
        corper = ensure_corper_profile(request.user)
        serializer = CorperProfileSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=corper)
        corper.refresh_from_db()
        sync_corper_approval_status(corper)
        return Response(CorperProfileSerializer(corper, context={"request": request}).data)
