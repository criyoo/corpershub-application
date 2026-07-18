import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.chat.models import Message
from apps.chat.services import get_community_unread_count, get_user_conversations
from apps.companies.models import CompanyProfile
from apps.common.models import CourseField
from apps.common.serializers import CourseFieldSerializer, SupportMessageSerializer
from apps.corpers.models import CorperProfile
from apps.interests.models import Interest
from apps.search.directory_stats import build_directory_stats
from apps.search.services import apply_company_recommendations, apply_corper_recommendations
from apps.subscriptions.services import get_latest_subscription

logger = logging.getLogger(__name__)


def health_check(_request):
    return JsonResponse({"status": "ok"})


class CourseCatalogAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, _request):
        fields = CourseField.objects.prefetch_related("categories__courses").all()
        serializer = CourseFieldSerializer(fields, many=True)
        return Response({"fields": serializer.data})


class DashboardOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        conversations = get_user_conversations(user)
        conversation_ids = conversations.values_list("id", flat=True)
        unread_message_count = (
            Message.objects.filter(
                conversation_id__in=conversation_ids,
                read_at__isnull=True,
            )
            .exclude(sender=user)
            .count()
        )
        subscription = get_latest_subscription(user=user, autocreate=False)

        if user.role == User.Role.COMPANY:
            response = self._company_overview(user=user)
        elif user.role == User.Role.CORPER:
            response = self._corper_overview(user=user)
        else:
            response = {
                "verification_credentials_outstanding": 0,
                "received_interest_count": 0,
                "sent_interest_count": 0,
                "online_count": 0,
                "strong_match_count": 0,
            }

        response.update(
            {
                "unread_message_count": unread_message_count,
                "conversation_count": conversations.count(),
                "current_subscription_plan": subscription.plan.name if subscription else None,
                "current_subscription_status": subscription.status if subscription else None,
            }
        )
        return Response(response)

    def _company_overview(self, *, user):
        company = getattr(user, "company_profile", None)
        outstanding_credentials = 0
        if company and company.approval_status != CompanyProfile.ApprovalStatus.APPROVED:
            outstanding_credentials = 1

        corpers = (
            CorperProfile.objects.select_related("user")
            .filter(
                user__is_active=True,
            )
            .filter(CorperProfile.directory_visibility_q())
        )
        scored_corpers = apply_corper_recommendations(viewer=user, corpers=corpers)

        return {
            "verification_credentials_outstanding": outstanding_credentials,
            "received_interest_count": Interest.objects.filter(
                company__user=user,
                corper_expressed_at__isnull=False,
            ).count(),
            "sent_interest_count": Interest.objects.filter(
                company__user=user,
                company_expressed_at__isnull=False,
            ).count(),
            "online_count": build_directory_stats(role=User.Role.CORPER)["online_count"],
            "strong_match_count": sum(1 for corper in scored_corpers if getattr(corper, "match_score", 0) > 50),
        }

    def _corper_overview(self, *, user):
        corper = getattr(user, "corper_profile", None)
        credential_statuses = [
            getattr(corper, "nin_verification_status", None),
            getattr(corper, "nysc_callup_verification_status", None),
            getattr(corper, "nysc_state_code_verification_status", None),
        ]
        outstanding_credentials = sum(status != "verified" for status in credential_statuses)

        companies = (
            CompanyProfile.objects.select_related("user")
            .filter(
                user__is_active=True,
                verification_status=CompanyProfile.VerificationStatus.VERIFIED,
                approval_status=CompanyProfile.ApprovalStatus.APPROVED,
            )
            .filter(CompanyProfile.directory_visibility_q())
        )
        scored_companies = apply_company_recommendations(viewer=user, companies=companies)

        community_unread_count = get_community_unread_count(user)

        return {
            "verification_credentials_outstanding": outstanding_credentials,
            "received_interest_count": Interest.objects.filter(
                corper__user=user,
                company_expressed_at__isnull=False,
            ).count(),
            "sent_interest_count": Interest.objects.filter(
                corper__user=user,
                corper_expressed_at__isnull=False,
            ).count(),
            "online_count": build_directory_stats(role=User.Role.COMPANY)["online_count"],
            "corpers_online_count": build_directory_stats(role=User.Role.CORPER)["online_count"],
            "strong_match_count": sum(1 for company in scored_companies if getattr(company, "match_score", 0) > 50),
            "community_unread_count": community_unread_count,
        }


class SupportMessageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SupportMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        user = request.user

        if payload["kind"] == "support":
            recipient = "support@corpershub.ng"
            subject = f"Support topic - {payload['topic']}"
            descriptor = f"Support topic: {payload['topic']}"
        else:
            recipient = "products@corpershub.ng"
            subject = f"Product Improvement Suggestions - {payload['title']}"
            descriptor = f"Improvement title: {payload['title']}"

        body = "\n".join(
            [
                f"Account email: {user.email}",
                f"Role: {user.role}",
                descriptor,
                "",
                payload["message"],
            ]
        )
        from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL

        try:
            send_mail(subject, body, from_email, [recipient], fail_silently=False)
        except (SMTPException, OSError) as exc:
            logger.exception("Unable to send support message", extra={"user_id": str(user.id), "kind": payload["kind"]})
            raise APIException("Unable to send message right now.") from exc

        return Response({"message": "Message sent successfully."})
