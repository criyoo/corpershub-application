from rest_framework import serializers

from apps.accounts.models import EmailDomainRule, User
from apps.adminpanel.models import AdminRegistrationRequest, PlatformOption
from apps.adminpanel.services import review_admin_registration_request
from apps.audit.models import AuditLog


class OverviewSerializer(serializers.Serializer):
    total_approved_corpers = serializers.IntegerField()
    total_approved_companies = serializers.IntegerField()
    total_pending_corpers = serializers.IntegerField()
    total_pending_companies = serializers.IntegerField()
    total_interests_by_companies = serializers.IntegerField()
    total_interests_by_corpers = serializers.IntegerField()
    total_conversations = serializers.IntegerField()
    pending_payments = serializers.IntegerField()


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "role", "email_verified", "is_active", "created_at", "updated_at")


class EmailDomainRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDomainRule
        fields = "__all__"


class PlatformOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformOption
        fields = "__all__"


class AdminRegistrationRequestSerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = AdminRegistrationRequest
        fields = (
            "id",
            "email",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "notification_sent_at",
            "created_at",
            "updated_at",
        )


class AdminRegistrationRequestReviewSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[
            (AdminRegistrationRequest.Status.APPROVED, "Approved"),
            (AdminRegistrationRequest.Status.REJECTED, "Rejected"),
        ]
    )

    class Meta:
        model = AdminRegistrationRequest
        fields = ("status",)

    def update(self, instance, validated_data):
        return review_admin_registration_request(
            request=instance,
            reviewer=self.context["request"].user,
            decision=validated_data["status"],
        )


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = ("id", "actor", "actor_email", "action", "target_type", "target_id", "metadata", "created_at")
