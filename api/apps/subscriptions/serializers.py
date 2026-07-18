from rest_framework import serializers

from apps.subscriptions.models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    amount_naira = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "code",
            "name",
            "description",
            "price_kobo",
            "amount_naira",
            "currency",
            "billing_interval",
            "applies_to",
            "features",
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_amount_naira(self, obj):
        return obj.price_kobo / 100


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = UserSubscription
        fields = (
            "id",
            "plan",
            "status",
            "starts_at",
            "ends_at",
            "next_billing_at",
            "is_auto_renew",
            "metadata",
            "created_at",
        )
