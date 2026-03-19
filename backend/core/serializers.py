from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Couple, CoupleMember, Invite

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    display_name = serializers.CharField(max_length=100)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="profile.display_name", read_only=True)
    avatar = serializers.ImageField(source="profile.avatar", read_only=True)
    timezone = serializers.CharField(source="profile.timezone", read_only=True)
    couple_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "avatar", "timezone", "couple_id"]
        read_only_fields = fields

    def get_couple_id(self, obj):
        membership = getattr(obj, "couple_membership", None)
        return membership.couple_id if membership else None


class CoupleMemberSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(
        source="user.profile.display_name", read_only=True
    )
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CoupleMember
        fields = ["id", "display_name", "email", "joined_at"]
        read_only_fields = fields


class CoupleSerializer(serializers.ModelSerializer):
    members = CoupleMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Couple
        fields = ["id", "name", "members", "created_at"]
        read_only_fields = fields


class InviteSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Invite
        fields = [
            "id",
            "code",
            "status",
            "invited_email",
            "invited_by_name",
            "created_at",
            "expires_at",
        ]
        read_only_fields = fields

    def get_invited_by_name(self, obj):
        if hasattr(obj.invited_by, "profile"):
            return obj.invited_by.profile.display_name
        return obj.invited_by.email
