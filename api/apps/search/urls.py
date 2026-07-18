from django.urls import path

from apps.search.views import CompanySearchAPIView, CompanySectorStatsAPIView, CorperSearchAPIView

urlpatterns = [
    path("corpers/", CorperSearchAPIView.as_view(), name="search-corpers"),
    path("companies/", CompanySearchAPIView.as_view(), name="search-companies"),
    path("company-sector-stats/", CompanySectorStatsAPIView.as_view(), name="company-sector-stats"),
]
