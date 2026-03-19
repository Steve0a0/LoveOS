from rest_framework import serializers

from .models import Note, NoteComment


class NoteCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = NoteComment
        fields = [
            "id",
            "content_type",
            "body",
            "gif_url",
            "author_name",
            "created_at",
        ]
        read_only_fields = ["id", "author_name", "created_at"]

    def get_author_name(self, obj):
        if hasattr(obj.author, "profile"):
            return obj.author.profile.display_name
        return obj.author.email


class NoteCommentCreateSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(
        choices=NoteComment.ContentType.choices, default="text"
    )
    body = serializers.CharField(max_length=2000)
    gif_url = serializers.URLField(max_length=500, required=False, default="", allow_blank=True)

    def validate(self, data):
        if data["content_type"] == "gif" and not data.get("gif_url"):
            raise serializers.ValidationError("gif_url is required for GIF comments.")
        return data


class NoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "body",
            "is_pinned",
            "open_when_type",
            "author_name",
            "comment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author_name", "comment_count", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if hasattr(obj.author, "profile"):
            return obj.author.profile.display_name
        return obj.author.email

    def get_comment_count(self, obj):
        return obj.comments.count()


class NoteDetailSerializer(NoteSerializer):
    """Note with all comments included."""
    comments = NoteCommentSerializer(many=True, read_only=True)

    class Meta(NoteSerializer.Meta):
        fields = NoteSerializer.Meta.fields + ["comments"]


class NoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["title", "body", "is_pinned", "open_when_type"]
