from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.interests.models import Interest
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationUnreadCountAPIView(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.role == "company":
            count = Interest.objects.filter(
                company__user=request.user,
                corper_expressed_at__isnull=False,
            ).count()
            new_count = Notification.objects.filter(
                recipient=request.user,
                notification_type=Notification.Type.CORPER_INTEREST_RECEIVED,
                read_at__isnull=True,
            ).count()
        elif request.user.role == "corper":
            count = Interest.objects.filter(
                corper__user=request.user,
                company_expressed_at__isnull=False,
            ).count()
            new_count = Interest.objects.filter(
                corper__user=request.user,
                company_expressed_at__isnull=False,
                viewed_by_corper_at__isnull=True,
            ).count()
        else:
            count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
            new_count = count
        return Response({"count": count, "new_count": new_count, "unread_count": new_count})


class NotificationMarkReadAPIView(APIView):
    def post(self, request, pk, *args, **kwargs):
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response({"message": "Marked as seen."})
