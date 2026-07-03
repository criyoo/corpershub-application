from django.urls import path

from apps.chat.views import (
    CommunityThreadAPIView,
    CommunityThreadMessagesAPIView,
    CommunityThreadsListAPIView,
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
    path("threads/", CommunityThreadsListAPIView.as_view(), name="community-threads"),
    path("threads/<str:topic>/", CommunityThreadAPIView.as_view(), name="community-thread"),
    path(
        "threads/<str:topic>/messages/",
        CommunityThreadMessagesAPIView.as_view(),
        name="community-thread-messages",
    ),
]
