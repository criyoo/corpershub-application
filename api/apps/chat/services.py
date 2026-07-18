from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count
from django.utils import timezone

from apps.chat.models import CommunityMessage, CommunityTopic, CommunityReadStatus, Conversation, Message

COMMUNITY_TOPICS = {
    "ppa-search": {
        "name": "PPA Placement Search",
        "description": "Discuss and share your experiences PPA placements",
    },
    "general-discussion": {
        "name": "General Discussion",
        "description": "Free for all chat about anything related to NYSC",
    },
    "camp-life": {
        "name": "Orientation Camp Life",
        "description": "Share your camp experiences, tips, and preparations",
    },
    "accommodation-allowance": {
        "name": "Accommodation & Allowance",
        "description": "Discuss monthly allowances, payments, and financial matters",
    },
}


def get_community_unread_count(user) -> int:
    """Get total unread community message count across all topics for a user."""
    topic_ids = list(COMMUNITY_TOPICS.keys())
    read_statuses = CommunityReadStatus.objects.filter(
        user=user, topic__topic_id__in=topic_ids
    )
    read_map = {rs.topic.topic_id: rs.last_read_at for rs in read_statuses}
    total_unread = 0
    for topic_id in topic_ids:
        last_read = read_map.get(topic_id)
        if last_read:
            unread = CommunityMessage.objects.filter(
                topic__topic_id=topic_id, created_at__gt=last_read
            ).count()
        else:
            unread = CommunityMessage.objects.filter(topic__topic_id=topic_id).count()
        total_unread += unread
    return total_unread


def get_user_community_topics(user):
    topics_from_db = CommunityTopic.objects.annotate(
        message_count=Count("messages", distinct=True)
    )
    db_map = {t.topic_id: t for t in topics_from_db}
    result = []
    for topic_id, info in COMMUNITY_TOPICS.items():
        if topic_id in db_map:
            result.append(db_map[topic_id])
        else:
            topic = CommunityTopic(topic_id=topic_id, name=info["name"], description=info.get("description", ""))
            topic.message_count = 0
            result.append(topic)

    if user:
        read_statuses = CommunityReadStatus.objects.filter(
            user=user, topic__topic_id__in=list(COMMUNITY_TOPICS.keys())
        ).select_related("topic")
        read_map = {}
        for rs in read_statuses:
            read_map[rs.topic.topic_id] = rs.last_read_at

        for topic in result:
            topic_id = topic.topic_id
            last_read = read_map.get(topic_id)
            if last_read:
                unread_count = CommunityMessage.objects.filter(
                    topic__topic_id=topic_id, created_at__gt=last_read
                ).count()
            else:
                unread_count = getattr(topic, "message_count", 0) or 0
            topic.unread_count = unread_count
    return result


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


# Community chat functions
def get_or_create_topic(topic_id: str):
    info = COMMUNITY_TOPICS.get(topic_id)
    topic_name = (info and info["name"]) or topic_id.replace("-", " ").title()
    description = info and info.get("description", "")
    return CommunityTopic.objects.get_or_create(
        topic_id=topic_id,
        defaults={"name": topic_name, "description": description},
    )[0]


def get_topic_with_message_count(topic_id: str, user=None):
    if topic_id not in COMMUNITY_TOPICS:
        return None
    info = COMMUNITY_TOPICS.get(topic_id, {})
    topic = CommunityTopic.objects.filter(topic_id=topic_id).annotate(
        message_count=Count("messages", distinct=True)
    ).first()
    if not topic:
        topic = CommunityTopic(topic_id=topic_id, name=info.get("name", topic_id), description=info.get("description", ""))
        topic.message_count = 0
    else:
        topic.message_count = topic.message_count if topic.message_count else 0
    topic.unread_count = getattr(topic, "message_count", 0)
    if user:
        read_status = CommunityReadStatus.objects.filter(
            user=user, topic__topic_id=topic_id
        ).first()
        if read_status:
            unread_count = CommunityMessage.objects.filter(
                topic__topic_id=topic_id, created_at__gt=read_status.last_read_at
            ).count()
            topic.unread_count = unread_count
    return topic


def get_community_thread(topic_id: str, user=None):
    topic = get_topic_with_message_count(topic_id, user=user)
    if not topic:
        return None
    messages = list(
        CommunityMessage.objects.filter(topic__topic_id=topic_id)
        .select_related("sender__corper_profile")
        .order_by("created_at")[:100]
    )
    return {"topic": topic, "messages": messages}


def create_community_message(*, topic_id: str, sender, content: str):
    topic = get_or_create_topic(topic_id)
    message = CommunityMessage.objects.create(topic=topic, sender=sender, content=content)
    return message


def mark_community_messages_read(*, topic_id: str, user):
    topic = CommunityTopic.objects.filter(topic_id=topic_id).first()
    if not topic:
        topic = get_or_create_topic(topic_id)
    read_status, _ = CommunityReadStatus.objects.get_or_create(
        user=user, topic=topic, defaults={"last_read_at": timezone.now()}
    )
    if _:
        return
    read_status.last_read_at = timezone.now()
    read_status.save(update_fields=["last_read_at", "updated_at"])


def broadcast_community_message(message):
    channel_layer = get_channel_layer()
    sender_profile = getattr(message.sender, "corper_profile", None)
    payload = {
        "type": "community.message",
        "message": {
            "id": str(message.id),
            "sender_id": str(message.sender_id),
            "sender_role": message.sender.role,
            "sender_name": sender_profile.full_name if sender_profile else None,
            "sender_profile_photo": sender_profile.profile_photo.url if sender_profile and sender_profile.profile_photo else None,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
    }
    async_to_sync(channel_layer.group_send)(f"community_{message.topic.topic_id}", payload)
