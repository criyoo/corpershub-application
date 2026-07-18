from collections import defaultdict

from apps.accounts.models import User
from rest_framework import generics
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
from apps.subscriptions.services import enforce_browse_access, enforce_corper_paid_access


NIGERIAN_STATES = (
    "Abia",
    "Adamawa",
    "Akwa Ibom",
    "Anambra",
    "Bauchi",
    "Bayelsa",
    "Benue",
    "Borno",
    "Cross River",
    "Delta",
    "Ebonyi",
    "Edo",
    "Ekiti",
    "Enugu",
    "Federal Capital Territory",
    "Gombe",
    "Imo",
    "Jigawa",
    "Kaduna",
    "Kano",
    "Katsina",
    "Kebbi",
    "Kogi",
    "Kwara",
    "Lagos",
    "Nasarawa",
    "Niger",
    "Ogun",
    "Ondo",
    "Osun",
    "Oyo",
    "Plateau",
    "Rivers",
    "Sokoto",
    "Taraba",
    "Yobe",
    "Zamfara",
)

STATE_BY_NORMALIZED_NAME = {state.lower(): state for state in NIGERIAN_STATES}
STATE_ALIASES = {
    "abuja": "Federal Capital Territory",
    "abuja fct": "Federal Capital Territory",
    "fct": "Federal Capital Territory",
    "federal capital territory fct": "Federal Capital Territory",
}


def _normalize_location_part(value: str) -> str:
    return " ".join(str(value or "").replace("(", " ").replace(")", " ").split()).strip()


def _canonical_state(value: str) -> str | None:
    normalized = _normalize_location_part(value)
    if not normalized:
        return None
    normalized_key = normalized.lower()
    if normalized_key.endswith(" state"):
        normalized_key = normalized_key.removesuffix(" state").strip()
    if normalized_key in STATE_ALIASES:
        return STATE_ALIASES[normalized_key]
    return STATE_BY_NORMALIZED_NAME.get(normalized_key)


def _split_company_states(value: str) -> list[str]:
    states = []
    for state_value in str(value or "").split(","):
        state = _canonical_state(state_value)
        if state and state not in states:
            states.append(state)
    return states


def _serialize_state_stats(state_stats: dict[str, dict]) -> list[dict]:
    serialized = []
    for state in NIGERIAN_STATES:
        stats = state_stats[state]
        cities = [
            {"city": city, "count": count}
            for city, count in sorted(stats["cities"].items(), key=lambda item: (-item[1], item[0]))
        ]
        serialized.append(
            {
                "state": state,
                "count": stats["count"],
                "cities": cities,
            }
        )
    return serialized


def build_company_sector_stats(sector: str) -> dict:
    queryset = (
        CompanyProfile.objects
        .filter(user__is_active=True, verification_status=CompanyProfile.VerificationStatus.VERIFIED)
        .filter(CompanyProfile.directory_visibility_q(), company_sector__iexact=sector)
    )
    state_stats = {
        state: {
            "count": 0,
            "cities": defaultdict(int),
        }
        for state in NIGERIAN_STATES
    }

    for company in queryset.only("company_location_state", "company_location_city"):
        city = _normalize_location_part(company.company_location_city) or "Unspecified"
        for state in _split_company_states(company.company_location_state):
            state_stats[state]["count"] += 1
            state_stats[state]["cities"][city] += 1

    return {
        "sector": sector,
        "total_companies": queryset.count(),
        "states": _serialize_state_stats(state_stats),
    }


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
        "desired_field_of_study",
        "desired_corper_description",
    ]
    ordering_fields = ["created_at", "company_name", "company_sector", "company_location_state"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(user__is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == "corper":
            if self.request.query_params.get("sector") or self.request.query_params.get("company_sector"):
                enforce_corper_paid_access(user=self.request.user)
            else:
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


class CompanySectorStatsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        sector = str(request.query_params.get("sector") or "").strip()
        if not sector:
            return Response({"detail": "Sector is required."}, status=400)
        return Response(build_company_sector_stats(sector))
