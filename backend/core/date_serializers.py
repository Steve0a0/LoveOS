from rest_framework import serializers

from .models import ImportantDate


class DateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ImportantDate
        fields = [
            "id",
            "title",
            "date",
            "date_type",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_by_name", "created_at"]

    def get_created_by_name(self, obj):
        if hasattr(obj.created_by, "profile"):
            return obj.created_by.profile.display_name
        return obj.created_by.email


class DateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportantDate
        fields = ["title", "date", "date_type"]
