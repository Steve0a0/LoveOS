"""Step 83 — Notification tests: subscribe, unsubscribe, trigger on actions."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status

from core.models import NotificationPreference, PushSubscription

from .helpers import auth_client, create_couple_pair, create_user, make_image


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class SubscribeTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("sub@test.com")
        self.client = auth_client(self.token)

    def test_subscribe(self):
        resp = self.client.post("/api/notifications/subscribe/", {
            "endpoint": "https://push.example.com/abc",
            "p256dh": "BNcR..." * 5,
            "auth_key": "authkey123",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PushSubscription.objects.filter(user=self.user).exists())

    def test_subscribe_idempotent(self):
        data = {
            "endpoint": "https://push.example.com/abc",
            "p256dh": "BNcR..." * 5,
            "auth_key": "authkey123",
        }
        self.client.post("/api/notifications/subscribe/", data, format="json")
        resp = self.client.post("/api/notifications/subscribe/", data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)

    def test_subscribe_missing_fields(self):
        resp = self.client.post("/api/notifications/subscribe/", {
            "endpoint": "https://push.example.com/abc",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class UnsubscribeTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("unsub@test.com")
        self.client = auth_client(self.token)
        self.endpoint = "https://push.example.com/remove"
        PushSubscription.objects.create(
            user=self.user,
            endpoint=self.endpoint,
            p256dh="key",
            auth_key="auth",
        )

    def test_unsubscribe(self):
        resp = self.client.post("/api/notifications/unsubscribe/", {
            "endpoint": self.endpoint,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PushSubscription.objects.filter(user=self.user).exists())

    def test_unsubscribe_unknown_endpoint(self):
        resp = self.client.post("/api/notifications/unsubscribe/", {
            "endpoint": "https://push.example.com/nonexistent",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class NotificationPreferenceTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("prefs@test.com")
        self.client = auth_client(self.token)

    def test_get_default_preferences(self):
        resp = self.client.get("/api/notifications/preferences/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["notes"])
        self.assertTrue(resp.data["memories"])
        self.assertTrue(resp.data["safety"])
        self.assertTrue(resp.data["location"])

    def test_update_preferences(self):
        resp = self.client.patch("/api/notifications/preferences/", {
            "notes": False,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["notes"])
        # Others unchanged
        self.assertTrue(resp.data["memories"])

    def test_vapid_key(self):
        resp = self.client.get("/api/notifications/vapid-key/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("public_key", resp.data)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class NotificationTriggerTests(TestCase):
    """Verify that creating notes, memories, and safety events trigger push notifications."""

    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)
        # Give user2 a push subscription
        PushSubscription.objects.create(
            user=self.u2,
            endpoint="https://push.example.com/u2",
            p256dh="key2",
            auth_key="auth2",
        )

    @patch("core.tasks.send_push_notification.delay")
    def test_note_triggers_notification(self, mock_push):
        self.client1.post("/api/notes/", {"title": "Hi", "body": "Love"})
        mock_push.assert_called()
        call_args = mock_push.call_args
        self.assertEqual(call_args[0][0], self.u2.pk)
        self.assertIn("note", call_args[1].get("category", call_args[0][3] if len(call_args[0]) > 3 else ""))

    @patch("core.tasks.send_push_notification.delay")
    def test_memory_triggers_notification(self, mock_push):
        img = make_image("JPEG")
        self.client1.post("/api/memories/", {"image": img, "caption": "Us"}, format="multipart")
        mock_push.assert_called()

    @patch("core.tasks.send_push_notification.delay")
    def test_safety_triggers_notification(self, mock_push):
        self.client1.post("/api/safety/check/", {"status": "leaving"}, format="json")
        mock_push.assert_called()

    @patch("core.tasks.send_push_notification.delay")
    def test_location_triggers_notification(self, mock_push):
        self.client1.post("/api/location/start/", {"duration_minutes": 15}, format="json")
        mock_push.assert_called()

    @patch("core.tasks.send_push_notification.delay")
    def test_disabled_preference_skips_notification(self, mock_push):
        """When notes are disabled for user2, creating a note should still call
        send_push_notification.delay (the preference check happens *inside* the task)."""
        NotificationPreference.objects.create(user=self.u2, notes=False)
        self.client1.post("/api/notes/", {"title": "X", "body": "Y"})
        # The task is still dispatched — the preference check runs inside the task
        mock_push.assert_called()
