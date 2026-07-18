from rest_framework import generics, permissions

from apps.common.permissions import IsAdminUserRole
from apps.subscriptions.models import SubscriptionPlan
from apps.subscriptions.serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer
from apps.subscriptions.services import list_user_subscriptions


class SubscriptionPlanListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUserRole()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = SubscriptionPlan.objects.all()
        if self.request.user.is_authenticated and self.request.user.role == "admin":
            return queryset
        queryset = queryset.filter(is_active=True)
        if not self.request.user.is_authenticated:
            return queryset
        if self.request.user.role != "corper":
            return queryset.none()
        return queryset.filter(applies_to=SubscriptionPlan.AppliesTo.CORPER)


class SubscriptionPlanDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminUserRole]
    queryset = SubscriptionPlan.objects.all()


class MySubscriptionAPIView(generics.ListAPIView):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return list_user_subscriptions(user=self.request.user)
