from rest_framework import serializers

from apps.common.models import CourseCategory, CourseField, UniversityCourse


class UniversityCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityCourse
        fields = ("id", "name")


class CourseCategorySerializer(serializers.ModelSerializer):
    courses = UniversityCourseSerializer(many=True, read_only=True)

    class Meta:
        model = CourseCategory
        fields = ("id", "name", "courses")


class CourseFieldSerializer(serializers.ModelSerializer):
    categories = CourseCategorySerializer(many=True, read_only=True)

    class Meta:
        model = CourseField
        fields = ("id", "name", "categories")


class SupportMessageSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[("support", "Support"), ("improvement", "Improvement")])
    topic = serializers.CharField(required=False, allow_blank=True, max_length=120)
    title = serializers.CharField(required=False, allow_blank=True, max_length=160)
    message = serializers.CharField()

    def validate(self, attrs):
        kind = attrs["kind"]
        topic = str(attrs.get("topic", "")).strip()
        title = str(attrs.get("title", "")).strip()
        message = str(attrs.get("message", "")).strip()

        if not message:
            raise serializers.ValidationError({"message": "Message is required."})
        attrs["message"] = message

        if kind == "support":
            if not topic:
                raise serializers.ValidationError({"topic": "Support topic is required."})
            attrs["topic"] = topic
        else:
            if not title:
                raise serializers.ValidationError({"title": "Title is required."})
            attrs["title"] = title
        return attrs
