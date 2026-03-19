from datetime import date

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Couple,
    ImportantDate,
    LocationShareSession,
    Memory,
    Note,
    SafeCheckEvent,
)
from .permissions import get_couple


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Return a summary of the couple's current state for the dashboard."""
    membership = getattr(request.user, "couple_membership", None)
    couple = get_couple(request.user)

    if not couple:
        return Response(
            {
                "paired": False,
                "couple": None,
                "days_together": None,
                "next_date": None,
                "latest_note": None,
                "latest_memory": None,
                "latest_safe_check": None,
                "active_location_session": None,
            }
        )

    # --- Days together ---
    days_together = None
    if couple.relationship_start_date:
        delta = date.today() - couple.relationship_start_date
        days_together = delta.days

    # --- Next important date ---
    today = date.today()
    next_date_obj = (
        ImportantDate.objects.filter(couple=couple, date__gte=today)
        .order_by("date")
        .first()
    )
    next_date = None
    if next_date_obj:
        next_date = {
            "id": next_date_obj.id,
            "title": next_date_obj.title,
            "date": next_date_obj.date.isoformat(),
            "date_type": next_date_obj.date_type,
            "days_away": (next_date_obj.date - today).days,
        }

    # --- Latest note (prefer pinned, then most recent) ---
    latest_note_obj = (
        Note.objects.filter(couple=couple)
        .order_by("-is_pinned", "-created_at")
        .first()
    )
    latest_note = None
    if latest_note_obj:
        author_name = (
            latest_note_obj.author.profile.display_name
            if hasattr(latest_note_obj.author, "profile")
            else latest_note_obj.author.email
        )
        latest_note = {
            "id": latest_note_obj.id,
            "title": latest_note_obj.title,
            "body": latest_note_obj.body[:120],
            "author": author_name,
            "is_pinned": latest_note_obj.is_pinned,
            "open_when_type": latest_note_obj.open_when_type,
            "created_at": latest_note_obj.created_at.isoformat(),
        }

    # --- Latest memory ---
    latest_memory_obj = (
        Memory.objects.filter(couple=couple)
        .select_related("uploaded_by__profile")
        .order_by("-created_at")
        .first()
    )
    latest_memory = None
    if latest_memory_obj:
        uploader_name = (
            latest_memory_obj.uploaded_by.profile.display_name
            if hasattr(latest_memory_obj.uploaded_by, "profile")
            else latest_memory_obj.uploaded_by.email
        )
        latest_memory = {
            "id": latest_memory_obj.id,
            "caption": latest_memory_obj.caption,
            "image": request.build_absolute_uri(latest_memory_obj.image.url)
            if latest_memory_obj.image
            else None,
            "thumbnail": request.build_absolute_uri(latest_memory_obj.thumbnail.url)
            if latest_memory_obj.thumbnail
            else None,
            "uploaded_by": uploader_name,
            "created_at": latest_memory_obj.created_at.isoformat(),
        }

    # --- Latest safe check ---
    latest_sc_obj = (
        SafeCheckEvent.objects.filter(couple=couple)
        .order_by("-created_at")
        .first()
    )
    latest_safe_check = None
    if latest_sc_obj:
        triggered_name = (
            latest_sc_obj.triggered_by.profile.display_name
            if hasattr(latest_sc_obj.triggered_by, "profile")
            else latest_sc_obj.triggered_by.email
        )
        latest_safe_check = {
            "id": latest_sc_obj.id,
            "status": latest_sc_obj.status,
            "status_display": latest_sc_obj.get_status_display(),
            "message": latest_sc_obj.message,
            "triggered_by": triggered_name,
            "created_at": latest_sc_obj.created_at.isoformat(),
        }

    # --- Active location session ---
    active_session = (
        LocationShareSession.objects.filter(
            couple=couple, status=LocationShareSession.Status.ACTIVE
        )
        .order_by("-started_at")
        .first()
    )
    # Inline expiry check
    if active_session and active_session.expires_at:
        from django.utils import timezone as tz

        if tz.now() >= active_session.expires_at:
            active_session.status = LocationShareSession.Status.EXPIRED
            active_session.ended_at = active_session.expires_at
            active_session.save(update_fields=["status", "ended_at"])
            active_session = None

    active_location_session = None
    if active_session:
        started_name = (
            active_session.started_by.profile.display_name
            if hasattr(active_session.started_by, "profile")
            else active_session.started_by.email
        )
        remaining = None
        if active_session.expires_at:
            from django.utils import timezone as tz

            remaining = max(
                0,
                int((active_session.expires_at - tz.now()).total_seconds()),
            )
        active_location_session = {
            "id": active_session.id,
            "started_by": started_name,
            "started_at": active_session.started_at.isoformat(),
            "time_remaining": remaining,
        }

    # --- Couple info ---
    members = []
    for m in couple.members.select_related("user__profile").all():
        members.append(
            {
                "id": m.user.id,
                "display_name": m.user.profile.display_name
                if hasattr(m.user, "profile")
                else m.user.email,
            }
        )

    couple_info = {
        "id": couple.id,
        "name": couple.name,
        "relationship_start_date": (
            couple.relationship_start_date.isoformat()
            if couple.relationship_start_date
            else None
        ),
        "members": members,
    }

    return Response(
        {
            "paired": True,
            "couple": couple_info,
            "days_together": days_together,
            "next_date": next_date,
            "latest_note": latest_note,
            "latest_memory": latest_memory,
            "latest_safe_check": latest_safe_check,
            "active_location_session": active_location_session,
        }
    )
