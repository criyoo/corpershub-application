from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.chat.models import Conversation, Message


def get_user_conversations(user):
    if user.role == "company":
        return Conversation.objects.filter(company=user)
    if user.role == "corper":
        return Conversation.objects.filter(corper=user)
    return Conversation.objects.all()


def get_conversation_or_raise(*, user, conversation_id):
    conversation = (
        Conversation.objects.select_related(
            "company",
            "corper",
            "interest",
            "company__company_profile",
            "corper__corper_profile",
        )
        .filter(pk=conversation_id)
        .first()
    )
    if not conversation:
        raise Conversation.DoesNotExist
    if user.role != "admin" and user not in {conversation.company, conversation.corper}:
        raise PermissionError("You are not a participant in this conversation.")
    return conversation


def create_message(*, conversation: Conversation, sender, content: str) -> Message:
    message = Message.objects.create(conversation=conversation, sender=sender, content=content)
    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return message


def unread_count_for_user(*, conversation: Conversation, user) -> int:
    return conversation.messages.exclude(sender=user).filter(read_at__isnull=True).count()


def mark_messages_read(*, conversation: Conversation, user):
    conversation.messages.exclude(sender=user).filter(read_at__isnull=True).update(
        read_at=timezone.now(),
        delivery_state=Message.DeliveryState.READ,
        updated_at=timezone.now(),
    )


def broadcast_message(message: Message):
    channel_layer = get_channel_layer()
    payload = {
        "type": "chat.message",
        "message": {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_id": str(message.sender_id),
            "sender_role": message.sender.role,
            "content": message.content,
            "delivery_state": message.delivery_state,
            "created_at": message.created_at.isoformat(),
        },
    }
    async_to_sync(channel_layer.group_send)(f"conversation_{message.conversation_id}", payload)


def broadcast_typing(*, conversation_id: str, sender_id: str):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"conversation_{conversation_id}",
        {
            "type": "chat.typing",
            "payload": {"conversation_id": conversation_id, "sender_id": sender_id},
        },
    )
