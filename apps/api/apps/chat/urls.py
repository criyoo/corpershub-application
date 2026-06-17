from django.urls import path

from apps.chat.views import (
    ConversationDetailAPIView,
    ConversationListAPIView,
    ConversationMarkReadAPIView,
    ConversationMessagesAPIView,
    InitiateConversationAPIView,
)

urlpatterns = [
    path("conversations/", ConversationListAPIView.as_view(), name="conversation-list"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailAPIView.as_view(), name="conversation-detail"),
    path("conversations/initiate/", InitiateConversationAPIView.as_view(), name="conversation-initiate"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        ConversationMessagesAPIView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/mark-read/",
        ConversationMarkReadAPIView.as_view(),
        name="conversation-mark-read",
    ),
]
