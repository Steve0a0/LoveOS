from rest_framework import serializers

from .models import LocationPoint, LocationShareSession


class LocationPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPoint
        fields = ["id", "latitude", "longitude", "accuracy", "recorded_at"]


class LocationSessionSerializer(serializers.ModelSerializer):
    started_by = serializers.SerializerMethodField()
    latest_point = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = LocationShareSession
        fields = [
            "id",
            "started_by",
            "status",
            "duration_minutes",
            "started_at",
            "expires_at",
            "ended_at",
            "latest_point",
            "time_remaining",
        ]

    def get_started_by(self, obj):
        if hasattr(obj.started_by, "profile"):
            return obj.started_by.profile.display_name
        return obj.started_by.email

    def get_latest_point(self, obj):
        point = obj.points.first()  # ordering is -recorded_at
        if point:
            return LocationPointSerializer(point).data
        return None

    def get_time_remaining(self, obj):
        if obj.expires_at and obj.is_active:
            from django.utils import timezone

            remaining = (obj.expires_at - timezone.now()).total_seconds()
            return max(0, int(remaining))
        return None


class StartSessionSerializer(serializers.Serializer):
    duration_minutes = serializers.IntegerField(min_value=5, max_value=480)


class UpdateLocationSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, default=None, allow_null=True)
