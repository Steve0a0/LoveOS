"""Step 82 — Location sharing tests: start, update, stop, expiry, permission denied."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from core.models import Couple, CoupleMember, LocationShareSession

from .helpers import auth_client, create_couple_pair, create_user

# Patch the scheduled expire task so eager-mode doesn't expire sessions immediately.
PATCH_EXPIRE = "core.tasks.expire_location_session.apply_async"


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LocationStartTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)

    @patch(PATCH_EXPIRE)
    def test_start_session(self, mock_expire):
        resp = self.client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "active")
        self.assertEqual(resp.data["duration_minutes"], 30)
        mock_expire.assert_called_once()

    @patch(PATCH_EXPIRE)
    def test_start_stops_previous_active(self, mock_expire):
        self.client1.post("/api/location/start/", {"duration_minutes": 15}, format="json")
        resp = self.client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # First session was stopped, second is active → exactly 1 active
        active = LocationShareSession.objects.filter(
            couple=self.couple, status=LocationShareSession.Status.ACTIVE
        ).count()
        self.assertEqual(active, 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LocationUpdateTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        with patch(PATCH_EXPIRE):
            resp = self.client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        self.session_id = resp.data["id"]

    def test_update_location(self):
        resp = self.client1.post("/api/location/update/", {
            "session_id": self.session_id,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy": 10.5,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["latitude"], "40.712800")

    def test_update_nonexistent_session(self):
        resp = self.client1.post("/api/location/update/", {
            "session_id": 99999,
            "latitude": 0, "longitude": 0,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LocationStopTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)

    @patch(PATCH_EXPIRE)
    def test_stop_session(self, _):
        self.client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        resp = self.client1.post("/api/location/stop/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "stopped")

    @patch(PATCH_EXPIRE)
    def test_partner_can_stop(self, _):
        self.client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        resp = self.client2.post("/api/location/stop/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_stop_no_active_session(self):
        resp = self.client1.post("/api/location/stop/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LocationExpiryTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)

    def _create_active_session(self, duration_minutes=1):
        """Create a session directly via ORM (avoids Celery eager-mode expiry)."""
        now = timezone.now()
        return LocationShareSession.objects.create(
            couple=self.couple,
            started_by=self.u1,
            duration_minutes=duration_minutes,
            expires_at=now + timedelta(minutes=duration_minutes),
            status=LocationShareSession.Status.ACTIVE,
        )

    def test_expired_session_detected_on_update(self):
        session = self._create_active_session()
        session.expires_at = timezone.now() - timedelta(minutes=5)
        session.save()

        resp = self.client1.post("/api/location/update/", {
            "session_id": session.pk,
            "latitude": 1.0, "longitude": 1.0,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_session_detected_on_current(self):
        session = self._create_active_session()
        session.expires_at = timezone.now() - timedelta(minutes=5)
        session.save()

        resp = self.client1.get("/api/location/current/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["active"])

    def test_celery_expire_task(self):
        from core.tasks import expire_location_session
        session = self._create_active_session()
        session.expires_at = timezone.now() - timedelta(minutes=1)
        session.save()
        # Run the celery task directly
        expire_location_session(session.pk)
        session.refresh_from_db()
        self.assertEqual(session.status, LocationShareSession.Status.EXPIRED)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LocationPermissionTests(TestCase):
    def test_unpaired_user_denied(self):
        _, token = create_user("solo@test.com")
        client = auth_client(token)
        resp = client.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        from rest_framework.test import APIClient
        client = APIClient()
        resp = client.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(PATCH_EXPIRE)
    def test_other_couple_cannot_update_session(self, _):
        u1, t1, u2, t2, couple1 = create_couple_pair()
        client1 = auth_client(t1)
        resp = client1.post("/api/location/start/", {"duration_minutes": 30}, format="json")
        session_id = resp.data["id"]

        # Create another couple
        u3, t3 = create_user("other1@test.com")
        u4, t4 = create_user("other2@test.com")
        c2 = Couple.objects.create(name="Other")
        CoupleMember.objects.create(couple=c2, user=u3)
        CoupleMember.objects.create(couple=c2, user=u4)
        client3 = auth_client(t3)

        resp2 = client3.post("/api/location/update/", {
            "session_id": session_id,
            "latitude": 0, "longitude": 0,
        }, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)
