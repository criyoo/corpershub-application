from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import EmailDomainRule, User
from apps.adminpanel.models import AdminRegistrationRequest, PlatformOption
from apps.adminpanel.serializers import (
    AdminRegistrationRequestReviewSerializer,
    AdminRegistrationRequestSerializer,
    AuditLogSerializer,
    EmailDomainRuleSerializer,
    OverviewSerializer,
    PlatformOptionSerializer,
    UserAdminSerializer,
)
from apps.audit.models import AuditLog
from apps.companies.models import CompanyProfile
from apps.chat.models import Conversation
from apps.common.permissions import IsAdminUserRole
from apps.interests.models import Interest
from apps.payments.models import PaymentTransaction
from apps.corpers.models import CorperProfile


class OverviewAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request, *args, **kwargs):
        payload = {
            "total_approved_corpers": CorperProfile.objects.filter(
                approval_status=CorperProfile.ApprovalStatus.APPROVED
            ).count(),
            "total_approved_companies": CompanyProfile.objects.filter(
                approval_status=CompanyProfile.ApprovalStatus.APPROVED
            ).count(),
            "total_pending_corpers": CorperProfile.objects.filter(
                approval_status=CorperProfile.ApprovalStatus.PENDING
            ).count(),
            "total_pending_companies": CompanyProfile.objects.filter(
                approval_status=CompanyProfile.ApprovalStatus.PENDING
            ).count(),
            "total_interests_by_companies": Interest.objects.filter(company_expressed_at__isnull=False).count(),
            "total_interests_by_corpers": Interest.objects.filter(corper_expressed_at__isnull=False).count(),
            "total_conversations": Conversation.objects.count(),
            "pending_payments": PaymentTransaction.objects.filter(status__in=["pending", "processing"]).count(),
        }
        return Response(OverviewSerializer(payload).data)


class UserAdminListAPIView(generics.ListAPIView):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = User.objects.all()
    search_fields = ["email", "role"]
    ordering_fields = ["created_at", "email", "role"]


class UserAdminDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUserRole]
    queryset = User.objects.all()


class EmailDomainRuleListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = EmailDomainRuleSerializer
    permission_classes = [IsAdminUserRole]
    queryset = EmailDomainRule.objects.all()
    search_fields = ["domain", "rule_type"]


class EmailDomainRuleDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = EmailDomainRuleSerializer
    permission_classes = [IsAdminUserRole]
    queryset = EmailDomainRule.objects.all()


class PlatformOptionListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlatformOptionSerializer
    permission_classes = [IsAdminUserRole]
    queryset = PlatformOption.objects.all()
    search_fields = ["label", "value", "category"]


class PlatformOptionDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = PlatformOptionSerializer
    permission_classes = [IsAdminUserRole]
    queryset = PlatformOption.objects.all()


class AuditLogListAPIView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUserRole]
    queryset = AuditLog.objects.select_related("actor").all()
    search_fields = ["action", "target_type", "actor__email"]
    ordering_fields = ["created_at", "action"]


class AdminRegistrationRequestListAPIView(generics.ListAPIView):
    serializer_class = AdminRegistrationRequestSerializer
    permission_classes = [IsAdminUserRole]
    queryset = AdminRegistrationRequest.objects.select_related("reviewed_by").all()
    search_fields = ["email", "status", "reviewed_by__email"]
    ordering_fields = ["created_at", "status", "reviewed_at"]


class AdminRegistrationRequestDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUserRole]
    queryset = AdminRegistrationRequest.objects.select_related("reviewed_by").all()

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return AdminRegistrationRequestReviewSerializer
        return AdminRegistrationRequestSerializer
