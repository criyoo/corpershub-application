from django.urls import path

from apps.common.views import CourseCatalogAPIView, DashboardOverviewAPIView, SupportMessageAPIView


urlpatterns = [
    path("course-catalog/", CourseCatalogAPIView.as_view(), name="course-catalog"),
    path("dashboard-overview/", DashboardOverviewAPIView.as_view(), name="dashboard-overview"),
    path("support-messages/", SupportMessageAPIView.as_view(), name="support-messages"),
]
