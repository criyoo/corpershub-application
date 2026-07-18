from django.urls import path

from apps.corpers.views import (
    MyCorperProfileAPIView,
    CorperProfileSubmitAPIView,
    CorperAdminDetailAPIView,
    CorperAdminListAPIView,
    CorperAdminVerificationDetailAPIView,
    CorperAdminVerificationListAPIView,
    CorperDirectoryDetailAPIView,
)

urlpatterns = [
    path("me/", MyCorperProfileAPIView.as_view(), name="corper-profile-me"),
    path("me/submit/", CorperProfileSubmitAPIView.as_view(), name="corper-profile-submit"),
    path("directory/<uuid:pk>/", CorperDirectoryDetailAPIView.as_view(), name="corper-directory-detail"),
    path("admin/", CorperAdminListAPIView.as_view(), name="corper-admin-list"),
    path(
        "admin/verifications/",
        CorperAdminVerificationListAPIView.as_view(),
        name="corper-admin-verification-list",
    ),
    path(
        "admin/verifications/<uuid:pk>/",
        CorperAdminVerificationDetailAPIView.as_view(),
        name="corper-admin-verification-detail",
    ),
    path("admin/<uuid:pk>/", CorperAdminDetailAPIView.as_view(), name="corper-admin-detail"),
]
