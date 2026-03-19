from rest_framework import serializers

from .models import Album, Memory


class AlbumSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = [
            "id",
            "title",
            "description",
            "cover",
            "created_by_name",
            "photo_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by_name", "photo_count", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        if hasattr(obj.created_by, "profile"):
            return obj.created_by.profile.display_name
        return obj.created_by.email

    def get_photo_count(self, obj):
        return obj.memories.count()

    def get_cover(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        # Use explicit cover_image if set
        if obj.cover_image:
            return request.build_absolute_uri(obj.cover_image.url)
        # Fall back to first memory's thumbnail
        first = obj.memories.exclude(thumbnail="").first()
        if first and first.thumbnail:
            return request.build_absolute_uri(first.thumbnail.url)
        first = obj.memories.first()
        if first and first.image:
            return request.build_absolute_uri(first.image.url)
        return None


class AlbumCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=1000, required=False, default="")


class AlbumUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(max_length=1000, required=False)


class AlbumDetailSerializer(AlbumSerializer):
    """Album with its photos included."""
    photos = serializers.SerializerMethodField()

    class Meta(AlbumSerializer.Meta):
        fields = AlbumSerializer.Meta.fields + ["photos"]

    def get_photos(self, obj):
        from .memory_serializers import MemorySerializer
        memories = obj.memories.select_related("uploaded_by__profile").all()
        return MemorySerializer(memories, many=True, context=self.context).data
