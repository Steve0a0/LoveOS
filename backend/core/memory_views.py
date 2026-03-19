import logging
import uuid
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .memory_serializers import MemoryCreateSerializer, MemorySerializer
from .models import Album, Memory
from .permissions import require_couple_response
from .tasks import generate_thumbnail

logger = logging.getLogger("loveos.audit")

# Compress uploaded images to this max dimension (preserving aspect ratio)
MAX_IMAGE_DIMENSION = 1920
COMPRESS_QUALITY = 85


def _safe_filename(original_name):
    """Generate a UUID-based filename preserving the original extension."""
    ext = ""
    if original_name and "." in original_name:
        ext = original_name.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "heic", "heif"):
        ext = "jpg"
    return f"{uuid.uuid4().hex}.{ext}"


def _compress_image(uploaded_file):
    """
    Resize large images down to MAX_IMAGE_DIMENSION and re-compress as JPEG.
    Returns an InMemoryUploadedFile ready for storage.
    """
    try:
        # Register HEIC/HEIF support if available
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        img = Image.open(uploaded_file)
        # Preserve EXIF orientation but strip metadata
        original_format = img.format
        width, height = img.size

        # Skip small images that don't need compression
        if width <= MAX_IMAGE_DIMENSION and height <= MAX_IMAGE_DIMENSION:
            uploaded_file.seek(0)
            return uploaded_file

        # Resize preserving aspect ratio
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

        # Convert RGBA/P to RGB for JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=COMPRESS_QUALITY, optimize=True)
        buf.seek(0)

        # Build a new name with .jpg extension
        new_name = uploaded_file.name.rsplit(".", 1)[0] + ".jpg" if "." in uploaded_file.name else uploaded_file.name + ".jpg"

        compressed = InMemoryUploadedFile(
            file=buf,
            field_name="image",
            name=new_name,
            content_type="image/jpeg",
            size=buf.getbuffer().nbytes,
            charset=None,
        )
        logger.info(
            "image.compressed original=%dx%d → %dx%d size=%dKB",
            width, height, img.size[0], img.size[1],
            compressed.size // 1024,
        )
        return compressed
    except Exception:
        logger.exception("image.compress_failed, using original")
        uploaded_file.seek(0)
        return uploaded_file


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def memory_list_create(request):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    if request.method == "GET":
        memories = (
            Memory.objects.filter(couple=couple)
            .select_related("uploaded_by__profile")
        )
        serializer = MemorySerializer(
            memories, many=True, context={"request": request}
        )
        return Response(serializer.data)

    # POST — multipart upload
    serializer = MemoryCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Compress large images before saving
        uploaded_file = _compress_image(serializer.validated_data["image"])
        # Rename file to a safe UUID-based name to prevent path traversal
        uploaded_file.name = _safe_filename(uploaded_file.name)

        # Resolve optional album
        album = None
        album_id = serializer.validated_data.get("album_id")
        if album_id:
            try:
                album = Album.objects.get(pk=album_id, couple=couple)
            except Album.DoesNotExist:
                return Response(
                    {"detail": "Album not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        memory = Memory.objects.create(
            couple=couple,
            uploaded_by=request.user,
            image=uploaded_file,
            caption=serializer.validated_data.get("caption", ""),
            album=album,
        )
    except Exception:
        logger.exception("memory.create_failed user=%s", request.user.pk)
        return Response(
            {"detail": "Image upload failed. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    logger.info("memory.created user=%s couple=%s memory=%s", request.user.pk, couple.pk, memory.pk)

    # Fire Celery task to generate thumbnail asynchronously
    generate_thumbnail.delay(memory.pk)

    # Notify partner
    from .tasks import notify_partner

    uploader_name = (
        request.user.profile.display_name
        if hasattr(request.user, "profile")
        else request.user.email
    )
    notify_partner.delay(
        request.user.pk,
        couple.pk,
        "New photo 📸",
        f"{uploader_name} added a new memory",
        "/timeline",
        "memories",
    )

    memory = Memory.objects.select_related("uploaded_by__profile").get(pk=memory.pk)
    return Response(
        MemorySerializer(memory, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def memory_detail(request, pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        memory = Memory.objects.get(pk=pk, couple=couple)
    except Memory.DoesNotExist:
        return Response(
            {"detail": "Memory not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    memory.image.delete(save=False)
    if memory.thumbnail:
        memory.thumbnail.delete(save=False)
    memory.delete()
    logger.info("memory.deleted user=%s couple=%s memory=%s", request.user.pk, couple.pk, pk)
    return Response(status=status.HTTP_204_NO_CONTENT)
