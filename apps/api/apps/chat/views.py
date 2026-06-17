from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationSerializer,
    InitiateConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.chat.services import (
    broadcast_message,
    create_message,
    get_conversation_or_raise,
    get_user_conversations,
    mark_messages_read,
)
from apps.common.permissions import IsAdminUserRole, IsCompanyUser, IsCorperUser
from apps.companies.models import CompanyProfile
from apps.companies.services import ensure_company_profile
from apps.interests.models import Interest
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.services import corper_has_paid_access, enforce_corper_paid_access

COMPANY_INTEREST_REQUIRED_MESSAGE = "Please indicate intereset in corper before initiating chat"
CORPER_INTEREST_REQUIRED_MESSAGE = "Please indicate intereset in company before initiating chat"
CORPER_WAIT_FOR_COMPANY_MESSAGE = "Please wait for company to indicate intereset before initiating chat"
CORPER_PAID_PLAN_REQUIRED_MESSAGE = "This corper needs an active paid plan before chat can start."


class ConversationListAPIView(generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        if self.request.user.role == "corper":
            enforce_corper_paid_access(user=self.request.user)
        return get_user_conversations(self.request.user).select_related(
            "company",
            "corper",
            "company__company_profile",
            "corper__corper_profile",
        )


class ConversationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ConversationSerializer
    lookup_url_kwarg = "conversation_id"

    def get_object(self):
        if self.request.user.role == "corper":
            enforce_corper_paid_access(user=self.request.user)
        return get_conversation_or_raise(user=self.request.user, conversation_id=self.kwargs["conversation_id"])


class InitiateConversationAPIView(APIView):
    permission_classes = [IsCompanyUser | IsCorperUser | IsAdminUserRole]

    def post(self, request, *args, **kwargs):
        serializer = InitiateConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        used_interest_id = serializer.validated_data.get("interest_id") is not None
        if request.user.role == "company" and not used_interest_id and not serializer.validated_data.get("corper_id"):
            return Response(
                {"detail": "Provide a corper_id or interest_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.role == "corper" and not used_interest_id and not serializer.validated_data.get("company_id"):
            return Response(
                {"detail": "Provide a company_id or interest_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        interest_queryset = Interest.objects.select_related(
            "corper",
            "corper__user",
            "company",
            "company__user",
        )
        interest = None
        company_profile = None
        if used_interest_id:
            interest = get_object_or_404(
                interest_queryset,
                pk=serializer.validated_data["interest_id"],
            )
            corper_profile = interest.corper
            company_profile = interest.company
        elif request.user.role == "company":
            company_profile = ensure_company_profile(request.user)
            corper_profile = get_object_or_404(
                CorperProfile.objects.select_related("user"),
                pk=serializer.validated_data["corper_id"],
            )
            interest = interest_queryset.filter(
                corper=corper_profile,
                company=company_profile,
            ).first()
        elif request.user.role == "corper":
            corper_profile = ensure_corper_profile(request.user)
            company_profile = get_object_or_404(
                CompanyProfile.objects.select_related("user"),
                pk=serializer.validated_data["company_id"],
            )
            interest = interest_queryset.filter(
                corper=corper_profile,
                company=company_profile,
            ).first()
        else:
            return Response(
                {"detail": "Admins can only initiate chat from an existing interest."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.role == "company":
            if interest and interest.company.user != request.user:
                return Response({"detail": "You can only initiate chat for your company interests."}, status=403)
            company_user = request.user
            if used_interest_id:
                if not (interest.company_expressed_at or interest.corper_expressed_at):
                    return Response({"detail": COMPANY_INTEREST_REQUIRED_MESSAGE}, status=403)
            elif not interest or interest.company_expressed_at is None:
                return Response({"detail": COMPANY_INTEREST_REQUIRED_MESSAGE}, status=403)
            notification_recipient = corper_profile.user
            notification_title = "A company has started a conversation"
            notification_body = "You can now chat with the company from your inbox."
        elif request.user.role == "corper":
            enforce_corper_paid_access(user=request.user)
            if used_interest_id and interest and interest.corper.user != request.user:
                return Response({"detail": "You can only initiate chat for your interests."}, status=403)
            if not interest or interest.corper_expressed_at is None:
                return Response({"detail": CORPER_INTEREST_REQUIRED_MESSAGE}, status=403)
            if interest.company_expressed_at is None:
                return Response({"detail": CORPER_WAIT_FOR_COMPANY_MESSAGE}, status=403)
            company_user = company_profile.user
            notification_recipient = company_user
            notification_title = "A corper has started a conversation"
            notification_body = "You can now chat with the corper from your inbox."
        else:
            company_user = company_profile.user
            notification_recipient = corper_profile.user
            notification_title = "A company has started a conversation"
            notification_body = "You can now chat with the company from your inbox."

        if not corper_has_paid_access(user=corper_profile.user):
            return Response({"detail": CORPER_PAID_PLAN_REQUIRED_MESSAGE}, status=403)

        conversation, created = Conversation.objects.get_or_create(
            company=company_user,
            corper=corper_profile.user,
            defaults={"initiated_by": request.user, "interest": interest},
        )
        if interest:
            interest.status = Interest.Status.CONTACTED
            interest.save(update_fields=["status", "updated_at"])
            if not conversation.interest:
                conversation.interest = interest
                conversation.save(update_fields=["interest", "updated_at"])

        create_notification(
            recipient=notification_recipient,
            notification_type=Notification.Type.NEW_CHAT_MESSAGE,
            title=notification_title,
            body=notification_body,
            data={"conversation_id": str(conversation.id)},
        )
        log_audit_event(
            actor=request.user,
            action="chat.initiated",
            target_type="conversation",
            target_id=str(conversation.id),
            metadata={"interest_id": str(interest.id) if interest else ""},
        )
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationMessagesAPIView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_conversation(self):
        if self.request.user.role == "corper":
            enforce_corper_paid_access(user=self.request.user)
        return get_conversation_or_raise(user=self.request.user, conversation_id=self.kwargs["conversation_id"])

    def get_queryset(self):
        conversation = self.get_conversation()
        if self.request.method == "GET":
            mark_messages_read(conversation=conversation, user=self.request.user)
        return Message.objects.filter(conversation=conversation).select_related("sender")

    def post(self, request, *args, **kwargs):
        conversation = self.get_conversation()
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = create_message(
            conversation=conversation,
            sender=request.user,
            content=serializer.validated_data["content"],
        )
        recipient = conversation.corper if request.user == conversation.company else conversation.company
        create_notification(
            recipient=recipient,
            notification_type=Notification.Type.NEW_CHAT_MESSAGE,
            title="New chat message",
            body="You have received a new message.",
            data={"conversation_id": str(conversation.id), "message_id": str(message.id)},
        )
        broadcast_message(message)
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationMarkReadAPIView(APIView):
    def post(self, request, *args, **kwargs):
        if request.user.role == "corper":
            enforce_corper_paid_access(user=request.user)
        conversation = get_conversation_or_raise(user=request.user, conversation_id=kwargs["conversation_id"])
        mark_messages_read(conversation=conversation, user=request.user)
        return Response(
            {
                "conversation_id": str(conversation.id),
                "unread_count": 0,
            }
        )
