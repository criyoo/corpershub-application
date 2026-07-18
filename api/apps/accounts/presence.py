from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

ONLINE_WINDOW = timedelta(minutes=5)
PRESENCE_TOUCH_INTERVAL = timedelta(seconds=60)


def get_online_presence_cutoff(*, current_time=None):
    timestamp = current_time or timezone.now()
    return timestamp - ONLINE_WINDOW


def touch_user_presence(*, user, current_time=None) -> None:
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return

    timestamp = current_time or timezone.now()
    if user.last_seen_at and (timestamp - user.last_seen_at) < PRESENCE_TOUCH_INTERVAL:
        return

    type(user).objects.filter(pk=user.pk).update(last_seen_at=timestamp)
    user.last_seen_at = timestamp


def clear_user_presence(*, user) -> None:
    if not getattr(user, "is_authenticated", False):
        return

    type(user).objects.filter(pk=user.pk).update(last_seen_at=None)
    user.last_seen_at = None
