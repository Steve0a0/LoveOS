"""Shared test helpers used across all test modules."""
import io

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Couple, CoupleMember, Profile

User = get_user_model()


def create_user(email="alice@test.com", password="testpass123", display_name="Alice"):
    """Create a user with profile and return (user, token)."""
    user = User.objects.create_user(username=email, email=email, password=password)
    Profile.objects.create(user=user, display_name=display_name)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def auth_client(token):
    """Return an APIClient authenticated via cookie."""
    client = APIClient()
    client.cookies["auth_token"] = token.key
    return client


def create_couple_pair(
    email1="alice@test.com",
    email2="bob@test.com",
    name1="Alice",
    name2="Bob",
):
    """Create two users, a couple, and return (user1, token1, user2, token2, couple)."""
    user1, token1 = create_user(email1, display_name=name1)
    user2, token2 = create_user(email2, display_name=name2)
    couple = Couple.objects.create(name="Test Couple")
    CoupleMember.objects.create(couple=couple, user=user1)
    CoupleMember.objects.create(couple=couple, user=user2)
    return user1, token1, user2, token2, couple


def make_image(fmt="JPEG", size=(100, 100), colour="red"):
    """Create a valid in-memory image file and return as SimpleUploadedFile."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, colour)
    img.save(buf, format=fmt)
    buf.seek(0)
    ext = "jpg" if fmt == "JPEG" else fmt.lower()
    ct = f"image/{'jpeg' if fmt == 'JPEG' else fmt.lower()}"
    return SimpleUploadedFile(f"photo.{ext}", buf.read(), content_type=ct)
