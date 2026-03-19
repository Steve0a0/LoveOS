"""Step 78 — Auth tests: signup, login, logout, access control."""
from django.test import TestCase, override_settings
from rest_framework import status

from .helpers import auth_client, create_user

from rest_framework.test import APIClient


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class SignupTests(TestCase):
    def test_signup_success(self):
        client = APIClient()
        resp = client.post("/api/auth/signup/", {
            "email": "new@test.com",
            "password": "securepass1",
            "display_name": "New User",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["email"], "new@test.com")
        self.assertEqual(resp.data["display_name"], "New User")
        # Cookie is set
        self.assertIn("auth_token", resp.cookies)

    def test_signup_duplicate_email(self):
        client = APIClient()
        client.post("/api/auth/signup/", {
            "email": "dupe@test.com",
            "password": "securepass1",
            "display_name": "First",
        })
        resp = client.post("/api/auth/signup/", {
            "email": "dupe@test.com",
            "password": "securepass1",
            "display_name": "Second",
        })
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_signup_missing_fields(self):
        client = APIClient()
        resp = client.post("/api/auth/signup/", {"email": "x@x.com"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LoginTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("login@test.com", "mypassword")

    def test_login_success(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {
            "email": "login@test.com",
            "password": "mypassword",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "login@test.com")
        self.assertIn("auth_token", resp.cookies)

    def test_login_wrong_password(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {
            "email": "login@test.com",
            "password": "wrongpass",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {
            "email": "nobody@test.com",
            "password": "whatever",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LogoutTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("logout@test.com")

    def test_logout_clears_token(self):
        client = auth_client(self.token)
        resp = client.post("/api/auth/logout/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Token should now be invalid
        resp2 = client.get("/api/auth/me/")
        self.assertEqual(resp2.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class AccessControlTests(TestCase):
    def test_unauthenticated_me(self):
        client = APIClient()
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_notes(self):
        client = APIClient()
        resp = client.get("/api/notes/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_dashboard(self):
        client = APIClient()
        resp = client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_me(self):
        _, token = create_user("me@test.com")
        client = auth_client(token)
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "me@test.com")

    def test_unpaired_user_gets_403_on_notes(self):
        _, token = create_user("solo@test.com")
        client = auth_client(token)
        resp = client.get("/api/notes/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
