"""Step 80 — Notes & dates tests: create, edit, delete, dashboard summary."""
from datetime import date, timedelta

from django.test import TestCase, override_settings
from rest_framework import status

from .helpers import auth_client, create_couple_pair, create_user


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class NoteTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)

    def test_create_note(self):
        resp = self.client1.post("/api/notes/", {
            "title": "Hello",
            "body": "Miss you!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["title"], "Hello")

    def test_list_notes(self):
        self.client1.post("/api/notes/", {"title": "N1", "body": "B1"})
        self.client2.post("/api/notes/", {"title": "N2", "body": "B2"})
        resp = self.client1.get("/api/notes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_edit_note(self):
        resp = self.client1.post("/api/notes/", {"title": "Old", "body": "Old body"})
        pk = resp.data["id"]
        resp2 = self.client1.patch(f"/api/notes/{pk}/", {"title": "New"}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["title"], "New")

    def test_partner_can_edit_note(self):
        resp = self.client1.post("/api/notes/", {"title": "Shared", "body": "x"})
        pk = resp.data["id"]
        resp2 = self.client2.patch(f"/api/notes/{pk}/", {"body": "Updated"}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["body"], "Updated")

    def test_delete_note(self):
        resp = self.client1.post("/api/notes/", {"title": "Delete me", "body": "x"})
        pk = resp.data["id"]
        resp2 = self.client1.delete(f"/api/notes/{pk}/")
        self.assertEqual(resp2.status_code, status.HTTP_204_NO_CONTENT)
        resp3 = self.client1.get("/api/notes/")
        self.assertEqual(len(resp3.data), 0)

    def test_other_couple_cannot_see_notes(self):
        self.client1.post("/api/notes/", {"title": "Secret", "body": "x"})
        # Create a different couple
        u3, t3 = create_user("outsider@test.com")
        u4, t4 = create_user("outsider2@test.com")
        from core.models import Couple, CoupleMember
        c2 = Couple.objects.create(name="Other")
        CoupleMember.objects.create(couple=c2, user=u3)
        CoupleMember.objects.create(couple=c2, user=u4)
        client3 = auth_client(t3)
        resp = client3.get("/api/notes/")
        self.assertEqual(len(resp.data), 0)

    def test_other_couple_cannot_access_note(self):
        resp = self.client1.post("/api/notes/", {"title": "Mine", "body": "x"})
        pk = resp.data["id"]
        u3, t3 = create_user("hacker@test.com")
        u4, t4 = create_user("hacker2@test.com")
        from core.models import Couple, CoupleMember
        c2 = Couple.objects.create(name="Hacker Couple")
        CoupleMember.objects.create(couple=c2, user=u3)
        CoupleMember.objects.create(couple=c2, user=u4)
        client3 = auth_client(t3)
        resp2 = client3.delete(f"/api/notes/{pk}/")
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class DateTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.client1 = auth_client(self.t1)
        self.client2 = auth_client(self.t2)

    def test_create_date(self):
        resp = self.client1.post("/api/dates/", {
            "title": "Anniversary",
            "date": "2026-06-15",
            "date_type": "anniversary",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["title"], "Anniversary")

    def test_edit_date(self):
        resp = self.client1.post("/api/dates/", {
            "title": "Birthday",
            "date": "2026-05-01",
            "date_type": "birthday",
        })
        pk = resp.data["id"]
        resp2 = self.client1.patch(f"/api/dates/{pk}/", {"title": "My Birthday"}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["title"], "My Birthday")

    def test_delete_date(self):
        resp = self.client1.post("/api/dates/", {
            "title": "Trip",
            "date": "2026-12-25",
        })
        pk = resp.data["id"]
        resp2 = self.client1.delete(f"/api/dates/{pk}/")
        self.assertEqual(resp2.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_couple_cannot_delete(self):
        resp = self.client1.post("/api/dates/", {"title": "Ours", "date": "2026-07-04"})
        pk = resp.data["id"]
        u3, t3 = create_user("other1@test.com")
        u4, t4 = create_user("other2@test.com")
        from core.models import Couple, CoupleMember
        c2 = Couple.objects.create(name="Other")
        CoupleMember.objects.create(couple=c2, user=u3)
        CoupleMember.objects.create(couple=c2, user=u4)
        client3 = auth_client(t3)
        resp2 = client3.delete(f"/api/dates/{pk}/")
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.u1, self.t1, self.u2, self.t2, self.couple = create_couple_pair()
        self.couple.relationship_start_date = date.today() - timedelta(days=100)
        self.couple.save()
        self.client1 = auth_client(self.t1)

    def test_dashboard_paired(self):
        resp = self.client1.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["paired"])
        self.assertEqual(resp.data["days_together"], 100)

    def test_dashboard_unpaired(self):
        u3, t3 = create_user("unpaired@test.com")
        client3 = auth_client(t3)
        resp = client3.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["paired"])

    def test_dashboard_shows_note(self):
        self.client1.post("/api/notes/", {"title": "Hi", "body": "There"})
        resp = self.client1.get("/api/dashboard/")
        self.assertIsNotNone(resp.data["latest_note"])
        self.assertEqual(resp.data["latest_note"]["title"], "Hi")

    def test_dashboard_shows_next_date(self):
        future = (date.today() + timedelta(days=7)).isoformat()
        self.client1.post("/api/dates/", {"title": "Next Date", "date": future})
        resp = self.client1.get("/api/dashboard/")
        self.assertIsNotNone(resp.data["next_date"])
        self.assertEqual(resp.data["next_date"]["title"], "Next Date")
