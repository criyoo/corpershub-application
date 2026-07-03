from apps.accounts.models import User
from rest_framework import generics
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.companies.models import CompanyProfile
from apps.companies.serializers import CompanyDiscoverySerializer
from apps.search.directory_stats import build_directory_stats
from apps.search.services import (
    apply_company_recommendations,
    apply_corper_recommendations,
    filter_companies_for_directory,
    filter_corpers_for_directory,
    sort_by_recommendation,
)
from apps.corpers.models import CorperProfile
from apps.corpers.serializers import CorperDirectorySerializer
from apps.subscriptions.services import enforce_browse_access


class CorperSearchAPIView(generics.ListAPIView):
    serializer_class = CorperDirectorySerializer
    permission_classes = [AllowAny]
    filter_backends = [OrderingFilter]
    queryset = CorperProfile.objects.select_related("user").all()
    search_fields = ["full_name", "field_of_study", "university", "skill", "bio"]
    ordering_fields = ["created_at", "graduation_year", "full_name"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(user__is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == "company":
            queryset = queryset.filter(CorperProfile.directory_visibility_q())
        elif not self.request.user.is_authenticated:
            queryset = queryset.filter(CorperProfile.directory_visibility_q())
        return filter_corpers_for_directory(
            queryset=queryset,
            params=self.request.query_params,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        corpers = apply_corper_recommendations(viewer=request.user, corpers=queryset)
        directory_stats = build_directory_stats(role=User.Role.CORPER)
        if self._use_recommendation_ordering():
            corpers = sort_by_recommendation(corpers)
        page = self.paginate_queryset(corpers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["directory_stats"] = directory_stats
            return response

        serializer = self.get_serializer(corpers, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "results": serializer.data,
                "directory_stats": directory_stats,
            }
        )

    def _use_recommendation_ordering(self) -> bool:
        ordering = (self.request.query_params.get("ordering") or "").strip()
        return not ordering or ordering in {"recommended", "-recommended"}


class CompanySearchAPIView(generics.ListAPIView):
    serializer_class = CompanyDiscoverySerializer
    permission_classes = [AllowAny]
    filter_backends = [OrderingFilter]
    queryset = CompanyProfile.objects.select_related("user").all()
    search_fields = [
        "company_name",
        "company_sector",
        "company_function",
        "desired_field_of_study",
        "desired_corper_description",
    ]
    ordering_fields = ["created_at", "company_name", "company_sector", "company_location_state"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(user__is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == "corper":
            enforce_browse_access(user=self.request.user)
        queryset = queryset.filter(CompanyProfile.directory_visibility_q())
        if self.request.user.is_authenticated and self.request.user.role == "corper":
            queryset = queryset.filter(verification_status=CompanyProfile.VerificationStatus.VERIFIED)
        else:
            queryset = queryset.filter(verification_status=CompanyProfile.VerificationStatus.VERIFIED).exclude(
                company_name=""
            )
        return filter_companies_for_directory(
            queryset=queryset,
            params=self.request.query_params,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        companies = apply_company_recommendations(viewer=request.user, companies=queryset)
        directory_stats = build_directory_stats(role=User.Role.COMPANY)
        if self._use_recommendation_ordering():
            companies = sort_by_recommendation(companies)
        page = self.paginate_queryset(companies)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["directory_stats"] = directory_stats
            return response

        serializer = self.get_serializer(companies, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "results": serializer.data,
                "directory_stats": directory_stats,
            }
        )

    def _use_recommendation_ordering(self) -> bool:
        ordering = (self.request.query_params.get("ordering") or "").strip()
        return not ordering or ordering in {"recommended", "-recommended"}
