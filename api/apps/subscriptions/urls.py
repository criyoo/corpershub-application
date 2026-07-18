from django.urls import path

from apps.subscriptions.views import (
    MySubscriptionAPIView,
    SubscriptionPlanDetailAPIView,
    SubscriptionPlanListCreateAPIView,
)

urlpatterns = [
    path("plans/", SubscriptionPlanListCreateAPIView.as_view(), name="subscription-plan-list"),
    path("plans/<uuid:pk>/", SubscriptionPlanDetailAPIView.as_view(), name="subscription-plan-detail"),
    path("me/", MySubscriptionAPIView.as_view(), name="my-subscriptions"),
]
