"""Step 81 — Upload tests: valid image, invalid file, large file, camera flow."""
import io
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status

from .helpers import auth_client, create_couple_pair, make_image


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class UploadValidImageTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)

    def test_upload_jpeg(self):
        img = make_image("JPEG")
        resp = self.client1.post("/api/memories/", {"image": img, "caption": "Beach"}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["caption"], "Beach")
        self.assertIn("image", resp.data)

    def test_upload_png(self):
        img = make_image("PNG")
        resp = self.client1.post("/api/memories/", {"image": img}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_upload_webp(self):
        img = make_image("WEBP")
        resp = self.client1.post("/api/memories/", {"image": img}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_list_memories(self):
        img = make_image("JPEG")
        self.client1.post("/api/memories/", {"image": img}, format="multipart")
        resp = self.client2.get("/api/memories/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_delete_memory(self):
        img = make_image("JPEG")
        with patch("core.memory_views.generate_thumbnail.delay"):
            resp = self.client1.post("/api/memories/", {"image": img}, format="multipart")
        pk = resp.data["id"]
        resp2 = self.client1.delete(f"/api/memories/{pk}/")
        self.assertEqual(resp2.status_code, status.HTTP_204_NO_CONTENT)
        resp3 = self.client1.get("/api/memories/")
        self.assertEqual(len(resp3.data), 0)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class UploadInvalidFileTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)

    def test_upload_text_file_rejected(self):
        fake = SimpleUploadedFile("hack.txt", b"not an image", content_type="text/plain")
        resp = self.client1.post("/api/memories/", {"image": fake}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_pdf_rejected(self):
        fake = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 fake content", content_type="application/pdf")
        resp = self.client1.post("/api/memories/", {"image": fake}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_exe_disguised_as_image_rejected(self):
        """Spoofed content-type but invalid image bytes — Pillow verify catches this."""
        fake = SimpleUploadedFile("evil.jpg", b"MZ\x90\x00" * 100, content_type="image/jpeg")
        resp = self.client1.post("/api/memories/", {"image": fake}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_no_file(self):
        resp = self.client1.post("/api/memories/", {}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class UploadLargeFileTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)

    def test_upload_over_10mb_rejected(self):
        """Test the serializer rejects files reported as >10MB."""
        from core.memory_serializers import MemoryCreateSerializer

        buf = io.BytesIO()
        img = Image.new("RGB", (100, 100), "blue")
        img.save(buf, format="JPEG")
        buf.seek(0)
        content = buf.read()
        fake_large = SimpleUploadedFile("big.jpg", content, content_type="image/jpeg")
        fake_large.size = 11 * 1024 * 1024  # 11 MB
        ser = MemoryCreateSerializer(data={"image": fake_large})
        self.assertFalse(ser.is_valid())
        self.assertIn("image", ser.errors)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class CameraUploadFlowTests(TestCase):
    """Simulate the camera capture upload — just a JPEG POST with multipart."""

    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)

    def test_camera_capture_upload(self):
        """Simulates a camera capture: a JPEG file is uploaded via multipart."""
        img = make_image("JPEG", size=(640, 480))
        resp = self.client1.post(
            "/api/memories/",
            {"image": img, "caption": "Selfie!"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["caption"], "Selfie!")
        # UUID-based filename
        self.assertNotIn("photo.jpg", resp.data.get("image", ""))

    def test_upload_shows_in_timeline(self):
        img = make_image("JPEG")
        self.client1.post("/api/memories/", {"image": img, "caption": "Timeline!"}, format="multipart")
        resp = self.client1.get("/api/timeline/?type=photos")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["type"], "photo")

    def test_other_couple_cannot_see_memory(self):
        img = make_image("JPEG")
        self.client1.post("/api/memories/", {"image": img}, format="multipart")
        from core.models import Couple, CoupleMember
        from .helpers import create_user
        u3, t3 = create_user("spy1@test.com")
        u4, t4 = create_user("spy2@test.com")
        c2 = Couple.objects.create(name="Spy Couple")
        CoupleMember.objects.create(couple=c2, user=u3)
        CoupleMember.objects.create(couple=c2, user=u4)
        client3 = auth_client(t3)
        resp = client3.get("/api/memories/")
        self.assertEqual(len(resp.data), 0)
