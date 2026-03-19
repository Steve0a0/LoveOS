import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .album_serializers import (
    AlbumCreateSerializer,
    AlbumDetailSerializer,
    AlbumSerializer,
    AlbumUpdateSerializer,
)
from .models import Album
from .permissions import require_couple_response

logger = logging.getLogger("loveos.audit")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def album_list_create(request):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    if request.method == "GET":
        albums = Album.objects.filter(couple=couple).select_related(
            "created_by__profile"
        )
        serializer = AlbumSerializer(albums, many=True, context={"request": request})
        return Response(serializer.data)

    # POST
    serializer = AlbumCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    album = Album.objects.create(
        couple=couple,
        created_by=request.user,
        title=serializer.validated_data["title"],
        description=serializer.validated_data.get("description", ""),
    )
    logger.info("album.created user=%s couple=%s album=%s", request.user.pk, couple.pk, album.pk)
    return Response(
        AlbumSerializer(album, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def album_detail(request, pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        album = Album.objects.get(pk=pk, couple=couple)
    except Album.DoesNotExist:
        return Response({"detail": "Album not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = AlbumDetailSerializer(album, context={"request": request})
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = AlbumUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field in ("title", "description"):
            if field in serializer.validated_data:
                setattr(album, field, serializer.validated_data[field])
        album.save()
        logger.info("album.updated user=%s couple=%s album=%s", request.user.pk, couple.pk, album.pk)
        return Response(AlbumSerializer(album, context={"request": request}).data)

    # DELETE
    album.delete()
    logger.info("album.deleted user=%s couple=%s album=%s", request.user.pk, couple.pk, pk)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def album_add_photos(request, pk):
    """Add existing memories to an album."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        album = Album.objects.get(pk=pk, couple=couple)
    except Album.DoesNotExist:
        return Response({"detail": "Album not found."}, status=status.HTTP_404_NOT_FOUND)

    memory_ids = request.data.get("memory_ids", [])
    if not isinstance(memory_ids, list) or not memory_ids:
        return Response({"detail": "Provide a list of memory_ids."}, status=status.HTTP_400_BAD_REQUEST)

    from .models import Memory
    updated = Memory.objects.filter(pk__in=memory_ids, couple=couple).update(album=album)
    logger.info("album.photos_added user=%s album=%s count=%s", request.user.pk, album.pk, updated)
    return Response({"added": updated})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def album_remove_photos(request, pk):
    """Remove memories from an album (doesn't delete them)."""
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        album = Album.objects.get(pk=pk, couple=couple)
    except Album.DoesNotExist:
        return Response({"detail": "Album not found."}, status=status.HTTP_404_NOT_FOUND)

    memory_ids = request.data.get("memory_ids", [])
    if not isinstance(memory_ids, list) or not memory_ids:
        return Response({"detail": "Provide a list of memory_ids."}, status=status.HTTP_400_BAD_REQUEST)

    from .models import Memory
    updated = Memory.objects.filter(pk__in=memory_ids, album=album, couple=couple).update(album=None)
    logger.info("album.photos_removed user=%s album=%s count=%s", request.user.pk, album.pk, updated)
    return Response({"removed": updated})
