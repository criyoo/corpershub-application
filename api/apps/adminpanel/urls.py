from django.urls import path

from apps.adminpanel.views import (
    AdminRegistrationRequestDetailAPIView,
    AdminRegistrationRequestListAPIView,
    AuditLogListAPIView,
    EmailDomainRuleDetailAPIView,
    EmailDomainRuleListCreateAPIView,
    OverviewAPIView,
    PlatformOptionDetailAPIView,
    PlatformOptionListCreateAPIView,
    UserAdminDetailAPIView,
    UserAdminListAPIView,
)

urlpatterns = [
    path("overview/", OverviewAPIView.as_view(), name="admin-overview"),
    path(
        "admin-registration-requests/",
        AdminRegistrationRequestListAPIView.as_view(),
        name="admin-registration-requests",
    ),
    path(
        "admin-registration-requests/<uuid:pk>/",
        AdminRegistrationRequestDetailAPIView.as_view(),
        name="admin-registration-request-detail",
    ),
    path("users/", UserAdminListAPIView.as_view(), name="admin-users"),
    path("users/<uuid:pk>/", UserAdminDetailAPIView.as_view(), name="admin-user-detail"),
    path("domain-rules/", EmailDomainRuleListCreateAPIView.as_view(), name="admin-domain-rules"),
    path("domain-rules/<uuid:pk>/", EmailDomainRuleDetailAPIView.as_view(), name="admin-domain-rule-detail"),
    path("options/", PlatformOptionListCreateAPIView.as_view(), name="admin-options"),
    path("options/<uuid:pk>/", PlatformOptionDetailAPIView.as_view(), name="admin-option-detail"),
    path("audit/", AuditLogListAPIView.as_view(), name="admin-audit"),
]
