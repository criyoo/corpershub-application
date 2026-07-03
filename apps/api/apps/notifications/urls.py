from django.urls import path

from apps.notifications.views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
    NotificationUnreadCountAPIView,
)

urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notifications-list"),
    path("unread-count/", NotificationUnreadCountAPIView.as_view(), name="notifications-unread-count"),
    path("<uuid:pk>/read/", NotificationMarkReadAPIView.as_view(), name="notifications-mark-read"),
]
