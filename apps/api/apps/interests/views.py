from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.companies.models import CompanyProfile
from apps.companies.services import ensure_company_profile
from apps.common.permissions import IsCompanyUser, IsCorperUser
from apps.interests.models import Interest
from apps.interests.serializers import (
    CompanyInterestSerializer,
    InterestCreateSerializer,
    CorperInterestSerializer,
)
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import UserSubscription
from apps.subscriptions.services import enforce_corper_paid_access


def annotate_corper_paid_access(queryset):
    active_paid_subscription = UserSubscription.objects.filter(
        user=OuterRef("corper__user"),
        status__in=[UserSubscription.Status.ACTIVE, UserSubscription.Status.CANCELLED],
        plan__price_kobo__gt=0,
    )
    return queryset.annotate(corper_has_paid_access=Exists(active_paid_subscription))


class ExpressInterestAPIView(APIView):
    permission_classes = [IsCorperUser]

    def post(self, request, company_id, *args, **kwargs):
        serializer = InterestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enforce_corper_paid_access(user=request.user)
        corper = ensure_corper_profile(request.user)
        company = get_object_or_404(CompanyProfile, pk=company_id)
        now = timezone.now()
        interest, created = Interest.objects.get_or_create(
            corper=corper,
            company=company,
            defaults={
                "message": serializer.validated_data.get("message", ""),
                "corper_expressed_at": now,
            },
        )
        is_new_corper_interest = created or interest.corper_expressed_at is None

        fields_to_update: list[str] = []
        if not created:
            if interest.corper_expressed_at is None:
                interest.corper_expressed_at = now
                fields_to_update.append("corper_expressed_at")
            if serializer.validated_data.get("message"):
                interest.message = serializer.validated_data["message"]
                fields_to_update.append("message")
            if fields_to_update:
                interest.save(update_fields=[*fields_to_update, "updated_at"])

        if is_new_corper_interest:
            create_notification(
                recipient=company.user,
                notification_type=Notification.Type.CORPER_INTEREST_RECEIVED,
                title="New corper interest received",
                body=f"{corper.full_name or 'A corper'} has indicated interest in your listing.",
                data={"interest_id": str(interest.id), "corper_id": str(corper.id)},
            )
        log_audit_event(
            actor=request.user,
            action="interest.expressed",
            target_type="interest",
            target_id=str(interest.id),
            metadata={"company_id": str(company.id)},
        )
        return Response(
            {"message": "Interest sent successfully.", "interest_id": str(interest.id)},
            status=status.HTTP_201_CREATED if is_new_corper_interest else status.HTTP_200_OK,
        )


class CompanyExpressInterestAPIView(APIView):
    permission_classes = [IsCompanyUser]

    def post(self, request, corper_id, *args, **kwargs):
        company = ensure_company_profile(request.user)
        corper = get_object_or_404(CorperProfile, pk=corper_id)
        now = timezone.now()

        interest, created = Interest.objects.get_or_create(
            corper=corper,
            company=company,
            defaults={"company_expressed_at": now},
        )

        if created:
            return Response(
                {"message": "Corper added to Interest.", "interest_id": str(interest.id)},
                status=status.HTTP_201_CREATED,
            )

        if interest.company_expressed_at is None:
            interest.company_expressed_at = now
            interest.save(update_fields=["company_expressed_at", "updated_at"])
            return Response(
                {"message": "Corper added to Interest.", "interest_id": str(interest.id)},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "This corper is already in Interest.", "interest_id": str(interest.id)},
            status=status.HTTP_200_OK,
        )


class MyInterestsAPIView(generics.ListAPIView):
    serializer_class = CorperInterestSerializer
    permission_classes = [IsCorperUser]

    def get_queryset(self):
        corper = ensure_corper_profile(self.request.user)
        return (
            Interest.objects.select_related("company", "company__user")
            .filter(corper=corper, corper_expressed_at__isnull=False)
            .order_by("-corper_expressed_at", "-created_at")
        )


class CorperInterestedCompaniesAPIView(generics.ListAPIView):
    serializer_class = CorperInterestSerializer
    permission_classes = [IsCorperUser]

    def get_queryset(self):
        corper = ensure_corper_profile(self.request.user)
        interests = (
            Interest.objects.select_related("company", "company__user")
            .filter(corper=corper, company_expressed_at__isnull=False)
            .order_by("-company_expressed_at", "-created_at")
        )
        interests.filter(viewed_by_corper_at__isnull=True).update(viewed_by_corper_at=timezone.now())
        return interests


class InterestedCorpersAPIView(generics.ListAPIView):
    serializer_class = CompanyInterestSerializer
    permission_classes = [IsCompanyUser]

    def get_queryset(self):
        interests = annotate_corper_paid_access(
            Interest.objects.select_related("corper", "corper__user")
            .filter(company__user=self.request.user, corper_expressed_at__isnull=False)
            .order_by("-corper_expressed_at", "-created_at")
        )
        interests.filter(viewed_by_company_at__isnull=True).update(viewed_by_company_at=timezone.now())
        return interests


class CompanySavedInterestsAPIView(generics.ListAPIView):
    serializer_class = CompanyInterestSerializer
    permission_classes = [IsCompanyUser]

    def get_queryset(self):
        return annotate_corper_paid_access(
            Interest.objects.select_related("corper", "corper__user")
            .filter(company__user=self.request.user, company_expressed_at__isnull=False)
            .order_by("-company_expressed_at", "-created_at")
        )
