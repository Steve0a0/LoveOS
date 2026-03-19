import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SafeCheckEvent
from .permissions import require_couple_response
from .safety_serializers import SafeCheckCreateSerializer, SafeCheckSerializer

logger = logging.getLogger("loveos.audit")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def safety_check(request):
    """Create a new safe-check event."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    ser = SafeCheckCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    event = SafeCheckEvent.objects.create(
        couple=couple,
        triggered_by=request.user,
        status=ser.validated_data["status"],
        message=ser.validated_data.get("message", ""),
    )
    logger.info(
        "safety.check user=%s couple=%s status=%s", request.user.pk, couple.pk, event.status
    )

    # Notify partner
    from .tasks import notify_partner

    user_name = (
        request.user.profile.display_name
        if hasattr(request.user, "profile")
        else request.user.email
    )
    status_label = event.get_status_display()
    notify_partner.delay(
        request.user.pk,
        couple.pk,
        "Safe check 🛡️",
        f"{user_name}: {status_label}",
        "/safe-check",
        "safety",
    )

    return Response(SafeCheckSerializer(event).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def safety_history(request):
    """List couple's safe-check events, newest first."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    events = SafeCheckEvent.objects.filter(couple=couple).select_related(
        "triggered_by__profile"
    )[:50]
    return Response(SafeCheckSerializer(events, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def safety_latest(request):
    """Return only the latest safe-check event."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    event = (
        SafeCheckEvent.objects.filter(couple=couple)
        .select_related("triggered_by__profile")
        .first()
    )
    if not event:
        return Response(None, status=status.HTTP_204_NO_CONTENT)
    return Response(SafeCheckSerializer(event).data)
