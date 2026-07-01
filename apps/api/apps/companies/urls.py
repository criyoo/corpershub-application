from django.urls import path

from apps.companies.views import (
    CompanyAdminDetailAPIView,
    CompanyAdminListAPIView,
    CompanyDirectoryDetailAPIView,
    MyCompanyProfileAPIView,
    CompanyProfileSubmitAPIView,
    CompanyVerificationAPIView,
)

urlpatterns = [
    path("me/", MyCompanyProfileAPIView.as_view(), name="company-profile-me"),
    path("me/verification/", CompanyVerificationAPIView.as_view(), name="company-profile-verification"),
    path("me/submit/", CompanyProfileSubmitAPIView.as_view(), name="company-profile-submit"),
    path("directory/<uuid:pk>/", CompanyDirectoryDetailAPIView.as_view(), name="company-directory-detail"),
    path("admin/", CompanyAdminListAPIView.as_view(), name="company-admin-list"),
    path("admin/<uuid:pk>/", CompanyAdminDetailAPIView.as_view(), name="company-admin-detail"),
]
