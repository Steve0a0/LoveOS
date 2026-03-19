import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Profile
from .permissions import require_couple_response

logger = logging.getLogger("loveos.audit")


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_settings(request):
    """Get or update the current user's profile (display_name, timezone)."""
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return Response({
            "display_name": profile.display_name,
            "timezone": profile.timezone,
        })

    display_name = request.data.get("display_name")
    timezone = request.data.get("timezone")

    if display_name is not None:
        if len(display_name) > 100:
            return Response(
                {"detail": "Display name too long (max 100)."}, status=status.HTTP_400_BAD_REQUEST
            )
        profile.display_name = display_name

    if timezone is not None:
        if len(timezone) > 50:
            return Response(
                {"detail": "Timezone too long (max 50)."}, status=status.HTTP_400_BAD_REQUEST
            )
        profile.timezone = timezone

    profile.save()

    # Return updated user data so the frontend context can refresh
    from .serializers import UserSerializer
    logger.info("settings.profile_updated user=%s", request.user.pk)
    return Response(UserSerializer(request.user).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def couple_settings(request):
    """Get or update couple settings (relationship_start_date)."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    if request.method == "GET":
        return Response({
            "name": couple.name,
            "relationship_start_date": (
                couple.relationship_start_date.isoformat()
                if couple.relationship_start_date
                else None
            ),
        })

    name = request.data.get("name")
    relationship_start_date = request.data.get("relationship_start_date")

    if name is not None:
        if len(name) > 150:
            return Response(
                {"detail": "Name too long (max 150)."}, status=status.HTTP_400_BAD_REQUEST
            )
        couple.name = name

    if relationship_start_date is not None:
        if relationship_start_date == "":
            couple.relationship_start_date = None
        else:
            from datetime import date as date_type
            try:
                couple.relationship_start_date = date_type.fromisoformat(relationship_start_date)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    couple.save()
    logger.info("settings.couple_updated user=%s couple=%s", request.user.pk, couple.pk)

    return Response({
        "name": couple.name,
        "relationship_start_date": (
            couple.relationship_start_date.isoformat()
            if couple.relationship_start_date
            else None
        ),
    })
