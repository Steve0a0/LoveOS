import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Note, NoteComment
from .note_serializers import (
    NoteCommentCreateSerializer,
    NoteCommentSerializer,
    NoteCreateSerializer,
    NoteDetailSerializer,
    NoteSerializer,
)
from .permissions import require_couple_response

logger = logging.getLogger("loveos.audit")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def note_list_create(request):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    if request.method == "GET":
        notes = (
            Note.objects.filter(couple=couple)
            .select_related("author__profile")
            .prefetch_related("comments")
            .order_by("-is_pinned", "-created_at")
        )
        return Response(NoteSerializer(notes, many=True).data)

    # POST
    serializer = NoteCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(couple=couple, author=request.user)
    # Re-serialize with read fields
    note = Note.objects.select_related("author__profile").get(pk=serializer.instance.pk)
    logger.info("note.created user=%s couple=%s note=%s", request.user.pk, couple.pk, note.pk)

    # Notify partner
    from .tasks import notify_partner

    author_name = (
        request.user.profile.display_name
        if hasattr(request.user, "profile")
        else request.user.email
    )
    notify_partner.delay(
        request.user.pk,
        couple.pk,
        "New note 💌",
        f"{author_name} left you a note",
        "/notes",
        "notes",
    )

    return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def note_detail(request, pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        note = Note.objects.select_related("author__profile").prefetch_related(
            "comments__author__profile"
        ).get(pk=pk, couple=couple)
    except Note.DoesNotExist:
        return Response(
            {"detail": "Note not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(NoteDetailSerializer(note).data)

    if request.method == "DELETE":
        logger.info("note.deleted user=%s couple=%s note=%s", request.user.pk, couple.pk, note.pk)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — both partners can edit
    serializer = NoteCreateSerializer(note, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    note.refresh_from_db()
    logger.info("note.updated user=%s couple=%s note=%s", request.user.pk, couple.pk, note.pk)
    return Response(NoteDetailSerializer(note).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def note_comments(request, pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        note = Note.objects.get(pk=pk, couple=couple)
    except Note.DoesNotExist:
        return Response({"detail": "Note not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        comments = (
            NoteComment.objects.filter(note=note)
            .select_related("author__profile")
        )
        return Response(NoteCommentSerializer(comments, many=True).data)

    # POST
    serializer = NoteCommentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    comment = NoteComment.objects.create(
        note=note,
        author=request.user,
        content_type=serializer.validated_data["content_type"],
        body=serializer.validated_data["body"],
        gif_url=serializer.validated_data.get("gif_url", ""),
    )
    logger.info("note_comment.created user=%s note=%s comment=%s", request.user.pk, note.pk, comment.pk)

    # Notify partner about the reply
    from .tasks import notify_partner

    author_name = (
        request.user.profile.display_name
        if hasattr(request.user, "profile")
        else request.user.email
    )
    notify_partner.delay(
        request.user.pk,
        couple.pk,
        "Reply on note 💬",
        f"{author_name} replied to a note",
        "/notes",
        "notes",
    )

    comment = NoteComment.objects.select_related("author__profile").get(pk=comment.pk)
    return Response(
        NoteCommentSerializer(comment).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def note_comment_detail(request, pk, comment_pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        comment = NoteComment.objects.get(
            pk=comment_pk, note__pk=pk, note__couple=couple
        )
    except NoteComment.DoesNotExist:
        return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)

    comment.delete()
    logger.info("note_comment.deleted user=%s note=%s comment=%s", request.user.pk, pk, comment_pk)
    return Response(status=status.HTTP_204_NO_CONTENT)
