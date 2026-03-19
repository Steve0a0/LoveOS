from rest_framework import serializers

from .models import SafeCheckEvent


class SafeCheckSerializer(serializers.ModelSerializer):
    triggered_by = serializers.SerializerMethodField()

    class Meta:
        model = SafeCheckEvent
        fields = ["id", "status", "message", "triggered_by", "created_at"]

    def get_triggered_by(self, obj):
        if hasattr(obj.triggered_by, "profile"):
            return obj.triggered_by.profile.display_name
        return obj.triggered_by.email


class SafeCheckCreateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SafeCheckEvent.Status.choices)
    message = serializers.CharField(max_length=300, required=False, default="", allow_blank=True)
