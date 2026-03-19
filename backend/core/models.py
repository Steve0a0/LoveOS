import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# ---------------------------------------------------------------------------
# Profile — extends the built-in User
# ---------------------------------------------------------------------------
class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=50, blank=True, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()


# ---------------------------------------------------------------------------
# Couple / CoupleMember
# ---------------------------------------------------------------------------
class Couple(models.Model):
    """A couple is a pair of users. Max 2 members enforced at the model level."""

    name = models.CharField(max_length=150, blank=True)
    relationship_start_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Couple {self.pk}"


class CoupleMember(models.Model):
    """
    Junction table: links a user to a couple.

    Business rules enforced:
    - A user can belong to only ONE active couple (unique on user).
    - A couple can have at most TWO members (validated in clean()).
    """

    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="members"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="couple_membership",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"], name="one_active_couple_per_user"
            ),
        ]

    def clean(self):
        # Enforce max 2 members per couple
        existing = (
            CoupleMember.objects.filter(couple=self.couple)
            .exclude(pk=self.pk)
            .count()
        )
        if existing >= 2:
            raise ValidationError("A couple can have at most two members.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} in {self.couple}"


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------
class Invite(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        DECLINED = "declined"
        EXPIRED = "expired"

    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="invites"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invites",
    )
    invited_email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invite {self.code} ({self.status})"


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------
class Note(models.Model):
    class OpenWhen(models.TextChoices):
        NORMAL = "normal", "Normal"
        SAD = "open_when_sad", "Open when sad"
        HAPPY = "open_when_happy", "Open when happy"
        MISS_ME = "open_when_miss_me", "Open when you miss me"

    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes"
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    is_pinned = models.BooleanField(default=False)
    open_when_type = models.CharField(
        max_length=20, choices=OpenWhen.choices, default=OpenWhen.NORMAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title or f"Note {self.pk}"


# ---------------------------------------------------------------------------
# NoteComment — replies on a note (text, emoji, GIF)
# ---------------------------------------------------------------------------
class NoteComment(models.Model):
    class ContentType(models.TextChoices):
        TEXT = "text", "Text"
        EMOJI = "emoji", "Emoji"
        GIF = "gif", "GIF"

    note = models.ForeignKey(
        Note, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="note_comments",
    )
    content_type = models.CharField(
        max_length=10, choices=ContentType.choices, default=ContentType.TEXT
    )
    body = models.TextField()
    gif_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on Note {self.note_id} by {self.author}"


# ---------------------------------------------------------------------------
# ImportantDate
# ---------------------------------------------------------------------------
class ImportantDate(models.Model):
    class DateType(models.TextChoices):
        ANNIVERSARY = "anniversary", "Anniversary"
        BIRTHDAY = "birthday", "Birthday"
        VISIT = "visit", "Visit"
        CUSTOM = "custom", "Custom"

    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="important_dates"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="important_dates",
    )
    title = models.CharField(max_length=200)
    date = models.DateField()
    date_type = models.CharField(
        max_length=20, choices=DateType.choices, default=DateType.CUSTOM
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.title} — {self.date}"


# ---------------------------------------------------------------------------
# Album (organise memories into collections, e.g. a trip)
# ---------------------------------------------------------------------------
class Album(models.Model):
    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="albums"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="albums",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="albums/covers/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Memory (photos / media that belong to a couple)
# ---------------------------------------------------------------------------
class Memory(models.Model):
    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="memories"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memories",
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memories",
    )
    image = models.ImageField(upload_to="memories/")
    thumbnail = models.ImageField(upload_to="memories/thumbs/", blank=True)
    caption = models.CharField(max_length=300, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "memories"
        ordering = ["-created_at"]

    def __str__(self):
        return self.caption or f"Memory {self.pk}"


# ---------------------------------------------------------------------------
# SafeCheckEvent
# ---------------------------------------------------------------------------
class SafeCheckEvent(models.Model):
    class Status(models.TextChoices):
        LEAVING = "leaving", "Leaving now"
        REACHED = "reached", "Reached safely"
        CHECK_IN = "check_in", "Quick check-in"

    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="safe_check_events"
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="safe_check_events",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CHECK_IN
    )
    message = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"SafeCheck {self.pk} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# LocationShareSession / LocationPoint
# ---------------------------------------------------------------------------
class LocationShareSession(models.Model):
    """
    A live-location sharing session. Business rules:
    - Optional (created only when the user explicitly starts sharing).
    - Must have a duration OR be explicitly stopped (ended_at set).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        STOPPED = "stopped", "Stopped"
        EXPIRED = "expired", "Expired"

    couple = models.ForeignKey(
        Couple, on_delete=models.CASCADE, related_name="location_sessions"
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_sessions",
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Auto-stop after this many minutes. Null means manual stop only.",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        ordering = ["-started_at"]

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE and self.ended_at is None

    def __str__(self):
        return f"LocationSession {self.pk} ({self.status})"


class LocationPoint(models.Model):
    session = models.ForeignKey(
        LocationShareSession, on_delete=models.CASCADE, related_name="points"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True, help_text="Accuracy in meters")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"({self.latitude}, {self.longitude}) @ {self.recorded_at}"


# ---------------------------------------------------------------------------
# PushSubscription
# ---------------------------------------------------------------------------
class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth_key = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint"], name="unique_push_sub_per_endpoint"
            ),
        ]

    def __str__(self):
        return f"PushSub for {self.user} ({self.endpoint[:40]}…)"


# ---------------------------------------------------------------------------
# NotificationPreference
# ---------------------------------------------------------------------------
class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_prefs",
    )
    notes = models.BooleanField(default=True)
    memories = models.BooleanField(default=True)
    safety = models.BooleanField(default=True)
    location = models.BooleanField(default=True)
    location_share_enabled = models.BooleanField(
        default=True, help_text="Allow partner to request location sharing"
    )

    def __str__(self):
        return f"NotifPrefs for {self.user}"
