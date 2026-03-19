from rest_framework import serializers

from .models import Memory

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


class MemorySerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Memory
        fields = [
            "id",
            "image",
            "thumbnail",
            "caption",
            "album",
            "uploaded_by_name",
            "taken_at",
            "created_at",
        ]
        read_only_fields = ["id", "uploaded_by_name", "created_at"]

    def get_uploaded_by_name(self, obj):
        if hasattr(obj.uploaded_by, "profile"):
            return obj.uploaded_by.profile.display_name
        return obj.uploaded_by.email

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None


class MemoryCreateSerializer(serializers.Serializer):
    image = serializers.ImageField()
    caption = serializers.CharField(max_length=300, required=False, default="")
    album_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_image(self, value):
        if value.content_type not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f"Unsupported image type: {value.content_type}. "
                f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
            )
        if value.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"Image too large ({value.size // (1024 * 1024)}MB). Max: 10MB."
            )

        # Verify actual file content with Pillow (not just Content-Type header)
        from PIL import Image

        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

        try:
            img = Image.open(value)
            img.verify()
        except Exception:
            raise serializers.ValidationError("File is not a valid image.")
        finally:
            value.seek(0)

        return value
