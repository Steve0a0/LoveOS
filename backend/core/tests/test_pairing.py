"""Step 79 — Pairing tests: invite create, accept, expiry, already-used."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from core.models import Couple, CoupleMember, Invite

from .helpers import auth_client, create_user


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class CreateCoupleTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("pair1@test.com")
        self.client = auth_client(self.token)

    def test_create_couple(self):
        resp = self.client.post("/api/couples/create/", {"name": "Us"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Us")

    def test_cannot_create_second_couple(self):
        self.client.post("/api/couples/create/", {"name": "First"})
        resp = self.client.post("/api/couples/create/", {"name": "Second"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class InviteCreateTests(TestCase):
    def setUp(self):
        self.user, self.token = create_user("inv1@test.com")
        self.client = auth_client(self.token)
        self.client.post("/api/couples/create/", {"name": "Inv Couple"})

    def test_create_invite(self):
        resp = self.client.post("/api/invites/create/")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("invite_link", resp.data)
        self.assertIn("code", resp.data)

    def test_invite_without_couple_fails(self):
        user2, token2 = create_user("inv2@test.com")
        client2 = auth_client(token2)
        resp = client2.post("/api/invites/create/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class InviteAcceptTests(TestCase):
    def setUp(self):
        self.user1, self.token1 = create_user("acc1@test.com", display_name="Acc1")
        self.client1 = auth_client(self.token1)
        self.client1.post("/api/couples/create/", {"name": "Pair"})
        resp = self.client1.post("/api/invites/create/")
        self.invite_code = resp.data["code"]

        self.user2, self.token2 = create_user("acc2@test.com", display_name="Acc2")
        self.client2 = auth_client(self.token2)

    def test_validate_invite(self):
        resp = self.client2.get(f"/api/invites/{self.invite_code}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["valid"])

    def test_accept_invite(self):
        resp = self.client2.post(f"/api/invites/{self.invite_code}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("couple", resp.data)
        # Verify membership created
        self.assertTrue(
            CoupleMember.objects.filter(user=self.user2).exists()
        )

    def test_cannot_accept_own_invite(self):
        resp = self.client1.post(f"/api/invites/{self.invite_code}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_used_invite(self):
        # Accept first
        self.client2.post(f"/api/invites/{self.invite_code}/accept/")
        # Try to accept again with a third user
        user3, token3 = create_user("acc3@test.com")
        client3 = auth_client(token3)
        resp = client3.post(f"/api/invites/{self.invite_code}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class InviteExpiryTests(TestCase):
    def test_expired_invite_rejected(self):
        user1, token1 = create_user("exp1@test.com")
        client1 = auth_client(token1)
        client1.post("/api/couples/create/", {"name": "Expire"})
        resp = client1.post("/api/invites/create/")
        code = resp.data["code"]

        # Manually expire the invite
        invite = Invite.objects.get(code=code)
        invite.expires_at = timezone.now() - timedelta(hours=1)
        invite.save()

        user2, token2 = create_user("exp2@test.com")
        client2 = auth_client(token2)
        resp = client2.post(f"/api/invites/{code}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", resp.data["detail"].lower())

    def test_already_paired_user_cannot_accept(self):
        # User3 is already in a couple
        user3, token3 = create_user("paired@test.com")
        c = Couple.objects.create(name="Existing")
        CoupleMember.objects.create(couple=c, user=user3)

        # Create an invite from user1
        user1, token1 = create_user("host@test.com")
        client1 = auth_client(token1)
        client1.post("/api/couples/create/", {"name": "New"})
        resp = client1.post("/api/invites/create/")
        code = resp.data["code"]

        client3 = auth_client(token3)
        resp = client3.post(f"/api/invites/{code}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
