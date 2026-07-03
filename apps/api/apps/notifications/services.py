from __future__ import annotations

from apps.notifications.models import Notification


def create_notification(*, recipient, notification_type: str, title: str, body: str, data=None):
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data or {},
    )
