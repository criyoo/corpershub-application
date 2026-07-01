from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class Conversation(UUIDPrimaryKeyModel):
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_conversations"
    )
    corper = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="corper_conversations")
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="initiated_conversations"
    )
    interest = models.OneToOneField(
        "interests.Interest", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversation"
    )
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["company", "corper"], name="unique_conversation_participants")]


class Message(UUIDPrimaryKeyModel):
    class DeliveryState(models.TextChoices):
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    delivery_state = models.CharField(max_length=20, choices=DeliveryState.choices, default=DeliveryState.SENT)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]


class CommunityTopic(UUIDPrimaryKeyModel):
    topic_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CommunityMessage(UUIDPrimaryKeyModel):
    topic = models.ForeignKey(CommunityTopic, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_messages")
    content = models.TextField()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["topic", "-created_at"]),
        ]

    def __str__(self):
        return f"Message by {self.sender_id} in {self.topic_id}"


class CommunityReadStatus(UUIDPrimaryKeyModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_read_statuses")
    topic = models.ForeignKey(CommunityTopic, on_delete=models.CASCADE, related_name="read_statuses")
    last_read_at = models.DateTimeField()

    class Meta:
        unique_together = [["user", "topic"]]

    def __str__(self):
        return f"Read status for {self.user_id} in {self.topic_id}"
