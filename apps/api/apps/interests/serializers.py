from rest_framework import serializers

from apps.companies.serializers import CompanyDiscoverySerializer
from apps.interests.models import Interest
from apps.corpers.serializers import CorperDirectorySerializer
from apps.subscriptions.services import corper_has_paid_access


class InterestCreateSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CorperInterestSerializer(serializers.ModelSerializer):
    company = CompanyDiscoverySerializer(read_only=True)

    class Meta:
        model = Interest
        fields = (
            "id",
            "company",
            "message",
            "status",
            "corper_expressed_at",
            "company_expressed_at",
            "created_at",
        )


class CompanyInterestSerializer(serializers.ModelSerializer):
    corper = CorperDirectorySerializer(read_only=True)
    corper_has_expressed_interest = serializers.SerializerMethodField()
    corper_has_paid_access = serializers.SerializerMethodField()

    class Meta:
        model = Interest
        fields = (
            "id",
            "corper",
            "message",
            "status",
            "corper_expressed_at",
            "company_expressed_at",
            "corper_has_expressed_interest",
            "corper_has_paid_access",
            "viewed_by_company_at",
            "created_at",
        )

    def get_corper_has_expressed_interest(self, obj):
        return obj.corper_expressed_at is not None

    def get_corper_has_paid_access(self, obj):
        annotated_value = getattr(obj, "corper_has_paid_access", None)
        if annotated_value is not None:
            return bool(annotated_value)
        return corper_has_paid_access(user=obj.corper.user)
