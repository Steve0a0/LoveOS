from rest_framework import serializers

from .models import NotificationPreference, PushSubscription


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["id", "endpoint", "created_at"]


class SubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    p256dh = serializers.CharField(max_length=200)
    auth_key = serializers.CharField(max_length=200)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["notes", "memories", "safety", "location", "location_share_enabled"]
