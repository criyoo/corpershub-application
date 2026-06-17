from django.urls import path

from apps.verification.views import (
    VerificationAttemptDetailAPIView,
    VerificationAttemptListCreateAPIView,
    VerificationReviewAPIView,
)

urlpatterns = [
    path("attempts/", VerificationAttemptListCreateAPIView.as_view(), name="verification-attempts"),
    path("attempts/<uuid:pk>/", VerificationAttemptDetailAPIView.as_view(), name="verification-attempt-detail"),
    path("attempts/<uuid:pk>/review/", VerificationReviewAPIView.as_view(), name="verification-review"),
]
