from itertools import chain
from operator import attrgetter

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Memory, Note
from .permissions import get_couple


def _actor_name(user):
    if hasattr(user, "profile") and user.profile.display_name:
        return user.profile.display_name
    return user.email


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def timeline(request):
    couple = get_couple(request.user)
    if not couple:
        return Response(
            {"detail": "You must be in a couple to view the timeline."},
            status=403,
        )

    filter_type = request.query_params.get("type", "all")

    items = []

    if filter_type in ("all", "notes"):
        notes = (
            Note.objects.filter(couple=couple)
            .select_related("author__profile")
            .order_by("-created_at")
        )
        for n in notes:
            items.append(
                {
                    "id": f"note-{n.pk}",
                    "type": "note",
                    "timestamp": n.created_at.isoformat(),
                    "actor": _actor_name(n.author),
                    "content": {
                        "id": n.pk,
                        "title": n.title,
                        "body": n.body[:200],
                        "is_pinned": n.is_pinned,
                        "open_when_type": n.open_when_type,
                    },
                }
            )

    if filter_type in ("all", "photos"):
        memories = (
            Memory.objects.filter(couple=couple)
            .select_related("uploaded_by__profile")
            .order_by("-created_at")
        )
        for m in memories:
            items.append(
                {
                    "id": f"memory-{m.pk}",
                    "type": "photo",
                    "timestamp": m.created_at.isoformat(),
                    "actor": _actor_name(m.uploaded_by),
                    "content": {
                        "id": m.pk,
                        "caption": m.caption,
                        "image": request.build_absolute_uri(m.image.url)
                        if m.image
                        else None,
                        "thumbnail": request.build_absolute_uri(m.thumbnail.url)
                        if m.thumbnail
                        else None,
                    },
                }
            )

    # Sort merged list by timestamp descending
    items.sort(key=lambda x: x["timestamp"], reverse=True)

    return Response(items)
