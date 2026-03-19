import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CoupleMember, LocationPoint, LocationShareSession
from .location_serializers import (
    LocationSessionSerializer,
    StartSessionSerializer,
    UpdateLocationSerializer,
)
from .permissions import require_couple_response

logger = logging.getLogger("loveos.audit")


def _expire_if_needed(session):
    """Check if a session has passed its expires_at and mark it expired."""
    if (
        session.status == LocationShareSession.Status.ACTIVE
        and session.expires_at
        and timezone.now() >= session.expires_at
    ):
        session.status = LocationShareSession.Status.EXPIRED
        session.ended_at = session.expires_at
        session.save(update_fields=["status", "ended_at"])
    return session


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def location_start(request):
    """Start a new live-location sharing session."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    # Stop any existing active session for THIS USER only (not the partner's)
    active = LocationShareSession.objects.filter(
        couple=couple,
        started_by=request.user,
        status=LocationShareSession.Status.ACTIVE,
    )
    active.update(
        status=LocationShareSession.Status.STOPPED, ended_at=timezone.now()
    )

    ser = StartSessionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    duration = ser.validated_data["duration_minutes"]
    now = timezone.now()
    expires_at = now + timedelta(minutes=duration)

    session = LocationShareSession.objects.create(
        couple=couple,
        started_by=request.user,
        duration_minutes=duration,
        expires_at=expires_at,
        status=LocationShareSession.Status.ACTIVE,
    )
    logger.info(
        "location.started user=%s couple=%s session=%s duration=%s",
        request.user.pk, couple.pk, session.pk, duration,
    )

    # Schedule Celery task to auto-expire
    from .tasks import expire_location_session, notify_partner

    expire_location_session.apply_async(
        args=[session.pk], eta=expires_at
    )

    # Notify partner
    user_name = (
        request.user.profile.display_name
        if hasattr(request.user, "profile")
        else request.user.email
    )
    notify_partner.delay(
        request.user.pk,
        couple.pk,
        "Location sharing 📍",
        f"{user_name} started sharing their location for {duration} min",
        "/live-location",
        "location",
    )

    return Response(
        LocationSessionSerializer(session).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def location_update(request):
    """Add a location point to the current user's active session."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    ser = UpdateLocationSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        session = LocationShareSession.objects.get(
            pk=ser.validated_data["session_id"],
            couple=couple,
            started_by=request.user,
        )
    except LocationShareSession.DoesNotExist:
        return Response(
            {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check expiry inline
    _expire_if_needed(session)

    if session.status != LocationShareSession.Status.ACTIVE:
        return Response(
            {"detail": "Session is no longer active."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    point = LocationPoint.objects.create(
        session=session,
        latitude=ser.validated_data["latitude"],
        longitude=ser.validated_data["longitude"],
        accuracy=ser.validated_data.get("accuracy"),
    )

    return Response(
        {
            "id": point.id,
            "latitude": str(point.latitude),
            "longitude": str(point.longitude),
            "accuracy": point.accuracy,
            "recorded_at": point.recorded_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def location_stop(request):
    """Stop the current user's active location sharing session."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    session = (
        LocationShareSession.objects.filter(
            couple=couple,
            started_by=request.user,
            status=LocationShareSession.Status.ACTIVE,
        )
        .order_by("-started_at")
        .first()
    )

    if not session:
        return Response(
            {"detail": "No active session."}, status=status.HTTP_404_NOT_FOUND
        )

    session.status = LocationShareSession.Status.STOPPED
    session.ended_at = timezone.now()
    session.save(update_fields=["status", "ended_at"])
    logger.info("location.stopped user=%s couple=%s session=%s", request.user.pk, couple.pk, session.pk)

    return Response(LocationSessionSerializer(session).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def location_current(request):
    """
    Get the current location state for the couple.
    Returns my_session (current user's active sharing) and
    partner_session (partner's active sharing) separately.
    """
    couple, err = require_couple_response(request.user)
    if err:
        return err

    # Find partner user id
    partner_ids = (
        CoupleMember.objects.filter(couple=couple)
        .exclude(user=request.user)
        .values_list("user_id", flat=True)
    )

    def _get_active_session(user_id):
        session = (
            LocationShareSession.objects.filter(
                couple=couple,
                started_by_id=user_id,
                status=LocationShareSession.Status.ACTIVE,
            )
            .select_related("started_by__profile")
            .order_by("-started_at")
            .first()
        )
        if session:
            _expire_if_needed(session)
            if session.status == LocationShareSession.Status.ACTIVE:
                return session
        return None

    my_session = _get_active_session(request.user.pk)
    partner_session = None
    for pid in partner_ids:
        partner_session = _get_active_session(pid)
        if partner_session:
            break

    return Response({
        "my_session": LocationSessionSerializer(my_session).data if my_session else None,
        "partner_session": LocationSessionSerializer(partner_session).data if partner_session else None,
    })
