from rest_framework import serializers

from apps.chat.models import Conversation, Message
from apps.chat.services import unread_count_for_user


def get_file_url(file_field) -> str | None:
    if not file_field:
        return None

    try:
        return file_field.url
    except (AttributeError, ValueError):
        return None


def get_corper_first_name(full_name: str) -> str:
    return next((part for part in full_name.split() if part.strip()), "Corper")


def get_company_acronym(company_name: str) -> str:
    words = [part.strip() for part in company_name.replace("&", " ").split() if part.strip()]
    significant_words = [word for word in words if word.lower() not in {"and", "of", "the", "for"}]
    source = significant_words or words

    if not source:
        return "CO"
    if len(source) == 1:
        return source[0][:3].upper()

    return "".join(word[0].upper() for word in source[:4])


def get_corper_qualification(corper) -> str:
    return " · ".join(part.strip() for part in [corper.degree, corper.field_of_study] if part and part.strip())


class MessageSerializer(serializers.ModelSerializer):
    sender_role = serializers.CharField(source="sender.role", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "sender_role",
            "content",
            "delivery_state",
            "read_at",
            "created_at",
        )
        read_only_fields = ("id", "conversation", "sender", "sender_role", "delivery_state", "read_at", "created_at")


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000)


class ConversationSerializer(serializers.ModelSerializer):
    counterpart = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_labels = serializers.SerializerMethodField()
    participant_names = serializers.SerializerMethodField()
    participant_images = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "interest",
            "counterpart",
            "participant_labels",
            "participant_names",
            "participant_images",
            "last_message_at",
            "created_at",
            "unread_count",
        )

    def get_counterpart(self, obj):
        request = self.context["request"]
        if request.user.role == "company":
            corper = obj.corper.corper_profile
            return {
                "id": str(corper.id),
                "role": "corper",
                "name": corper.full_name,
                "qualification": get_corper_qualification(corper),
                "degree": corper.degree,
                "field_of_study": corper.field_of_study,
                "location": corper.posting_location_state,
                "image": get_file_url(corper.profile_photo),
            }
        company = obj.company.company_profile
        return {
            "id": str(company.id),
            "role": "company",
            "name": company.company_name,
            "location": f"{company.company_location_city}, {company.company_location_state}".strip(", "),
            "sector": company.company_sector,
            "image": get_file_url(company.company_image),
        }

    def get_unread_count(self, obj):
        return unread_count_for_user(conversation=obj, user=self.context["request"].user)

    def get_participant_labels(self, obj):
        corper_name = ""
        if hasattr(obj.corper, "corper_profile"):
            corper_name = obj.corper.corper_profile.full_name or ""

        company_name = ""
        if hasattr(obj.company, "company_profile"):
            company_name = obj.company.company_profile.company_name or ""

        return {
            "corper": get_corper_first_name(corper_name),
            "company": get_company_acronym(company_name),
        }

    def get_participant_names(self, obj):
        corper_name = ""
        if hasattr(obj.corper, "corper_profile"):
            corper_name = obj.corper.corper_profile.full_name or ""

        company_name = ""
        if hasattr(obj.company, "company_profile"):
            company_name = obj.company.company_profile.company_name or ""

        return {
            "corper": corper_name or "Corper",
            "company": company_name or "Company",
        }

    def get_participant_images(self, obj):
        corper_image = None
        if hasattr(obj.corper, "corper_profile"):
            corper_image = get_file_url(obj.corper.corper_profile.profile_photo)

        company_image = None
        if hasattr(obj.company, "company_profile"):
            company_image = get_file_url(obj.company.company_profile.company_image)

        return {
            "corper": corper_image,
            "company": company_image,
        }


class InitiateConversationSerializer(serializers.Serializer):
    corper_id = serializers.UUIDField(required=False)
    company_id = serializers.UUIDField(required=False)
    interest_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        identifiers = [
            attrs.get("corper_id"),
            attrs.get("company_id"),
            attrs.get("interest_id"),
        ]
        provided_count = sum(1 for identifier in identifiers if identifier)
        if provided_count != 1:
            raise serializers.ValidationError(
                "Provide exactly one of corper_id, company_id, or interest_id."
            )
        return attrs
