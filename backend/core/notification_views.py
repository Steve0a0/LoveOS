from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import NotificationPreference, PushSubscription
from .notification_serializers import (
    NotificationPreferenceSerializer,
    PushSubscriptionSerializer,
    SubscribeSerializer,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe(request):
    """Register a push subscription for the current user."""
    ser = SubscribeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    sub, created = PushSubscription.objects.update_or_create(
        user=request.user,
        endpoint=ser.validated_data["endpoint"],
        defaults={
            "p256dh": ser.validated_data["p256dh"],
            "auth_key": ser.validated_data["auth_key"],
        },
    )
    return Response(
        PushSubscriptionSerializer(sub).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unsubscribe(request):
    """Remove a push subscription."""
    endpoint = request.data.get("endpoint", "")
    deleted, _ = PushSubscription.objects.filter(
        user=request.user, endpoint=endpoint
    ).delete()
    if deleted:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {"detail": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preference toggles."""
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return Response(NotificationPreferenceSerializer(prefs).data)

    ser = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vapid_public_key(request):
    """Return the VAPID public key so the frontend can subscribe."""
    from django.conf import settings as django_settings

    return Response({"public_key": django_settings.VAPID_PUBLIC_KEY})
