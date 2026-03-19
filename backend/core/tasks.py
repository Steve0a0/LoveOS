import json
import logging
from datetime import date, timedelta
from io import BytesIO

from celery import shared_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------
THUMBNAIL_SIZE = (400, 400)


@shared_task(name="core.generate_thumbnail")
def generate_thumbnail(memory_id):
    """
    Generate a thumbnail for a Memory image.
    Runs asynchronously via Celery so the upload response is fast.
    """
    from django.core.files.base import ContentFile

    from PIL import Image

    from .models import Memory

    try:
        memory = Memory.objects.get(pk=memory_id)
    except Memory.DoesNotExist:
        logger.warning("[THUMB] Memory %s not found, skipping.", memory_id)
        return

    if not memory.image:
        return

    try:
        img = Image.open(memory.image)
        img.thumbnail(THUMBNAIL_SIZE)

        # Convert to RGB if needed (e.g. RGBA PNGs)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)

        thumb_name = f"thumb_{memory.pk}.jpg"
        memory.thumbnail.save(thumb_name, ContentFile(buf.read()), save=True)

        logger.info("[THUMB] Generated thumbnail for Memory %s", memory_id)
    except Exception:
        logger.exception("[THUMB] Failed to generate thumbnail for Memory %s", memory_id)


@shared_task(name="core.check_upcoming_dates")
def check_upcoming_dates():
    """
    Runs daily. Finds important dates happening in the next 1, 3, or 7 days
    and logs reminders. In production this would trigger push notifications
    or emails to the couple members.
    """
    from .models import ImportantDate

    today = date.today()
    thresholds = [1, 3, 7]

    for days_ahead in thresholds:
        target = today + timedelta(days=days_ahead)
        upcoming = ImportantDate.objects.filter(date=target).select_related(
            "couple", "created_by"
        )
        for imp_date in upcoming:
            logger.info(
                "[REMINDER] '%s' for couple %s is in %d day(s) (%s)",
                imp_date.title,
                imp_date.couple_id,
                days_ahead,
                imp_date.date,
            )
            # TODO: send push notification / email to couple members


@shared_task(name="core.send_daily_digest")
def send_daily_digest():
    """
    Runs daily. Builds a summary of things happening today for each couple:
    - Important dates happening today
    - Unacknowledged safe-check events
    """
    from .models import Couple, ImportantDate

    today = date.today()
    couples_with_dates = (
        ImportantDate.objects.filter(date=today)
        .values_list("couple_id", flat=True)
        .distinct()
    )

    couple_ids = set(couples_with_dates)
    if not couple_ids:
        logger.info("[DIGEST] No digests to send today.")
        return

    for couple in Couple.objects.filter(id__in=couple_ids):
        todays_dates = ImportantDate.objects.filter(couple=couple, date=today)
        logger.info(
            "[DIGEST] Couple %s: %d date(s) today",
            couple.id,
            todays_dates.count(),
        )
        # TODO: send push notification / email


@shared_task(name="core.expire_old_invites")
def expire_old_invites():
    """
    Runs daily. Marks pending invites older than 7 days as expired.
    """
    from django.utils import timezone

    from .models import Invite

    cutoff = timezone.now() - timedelta(days=7)
    expired = Invite.objects.filter(
        status=Invite.Status.PENDING, created_at__lt=cutoff
    ).update(status=Invite.Status.EXPIRED)

    if expired:
        logger.info("[INVITES] Expired %d old invite(s).", expired)


@shared_task(name="core.expire_location_session")
def expire_location_session(session_id):
    """
    Auto-expire a location sharing session when its duration elapses.
    Scheduled via apply_async(eta=expires_at) when a session is created.
    """
    from .models import LocationShareSession

    try:
        session = LocationShareSession.objects.get(pk=session_id)
    except LocationShareSession.DoesNotExist:
        logger.warning("[LOCATION] Session %s not found, skipping.", session_id)
        return

    if session.status != LocationShareSession.Status.ACTIVE:
        logger.info("[LOCATION] Session %s already %s, skipping.", session_id, session.status)
        return

    session.status = LocationShareSession.Status.EXPIRED
    session.ended_at = session.expires_at or session.started_at
    session.save(update_fields=["status", "ended_at"])
    logger.info("[LOCATION] Session %s expired by Celery.", session_id)


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------
@shared_task(name="core.send_push_notification")
def send_push_notification(user_id, title, body, url="/dashboard", category="notes"):
    """
    Send a web push notification to all subscriptions of a user.
    Respects the user's notification preferences.
    category: one of 'notes', 'memories', 'safety', 'location'
    """
    from django.conf import settings as django_settings

    from pywebpush import WebPushException, webpush

    from .models import NotificationPreference, PushSubscription

    # Check notification preference
    try:
        prefs = NotificationPreference.objects.get(user_id=user_id)
        if not getattr(prefs, category, True):
            logger.info("[PUSH] User %s has %s notifications disabled.", user_id, category)
            return
    except NotificationPreference.DoesNotExist:
        pass  # defaults are all True

    subscriptions = PushSubscription.objects.filter(user_id=user_id)
    if not subscriptions.exists():
        logger.info("[PUSH] No subscriptions for user %s.", user_id)
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    vapid_private_key = django_settings.VAPID_PRIVATE_KEY
    vapid_claims = {"sub": django_settings.VAPID_ADMIN_EMAIL}

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth_key},
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
                ttl=86400,
            )
            logger.info("[PUSH] Sent to user %s endpoint %s…", user_id, sub.endpoint[:40])
        except WebPushException as e:
            logger.warning("[PUSH] Failed for user %s: %s", user_id, e)
            # If endpoint is gone (410), remove the subscription
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 410:
                sub.delete()
                logger.info("[PUSH] Removed stale subscription for user %s.", user_id)
        except Exception:
            logger.exception("[PUSH] Unexpected error for user %s.", user_id)


@shared_task(name="core.notify_partner")
def notify_partner(triggering_user_id, couple_id, title, body, url="/dashboard", category="notes"):
    """
    Celery task: send a push notification to the partner (the other member of the couple).
    Accepts IDs so the task is fully serialisable.
    """
    from .models import CoupleMember

    partner_ids = (
        CoupleMember.objects.filter(couple_id=couple_id)
        .exclude(user_id=triggering_user_id)
        .values_list("user_id", flat=True)
    )
    for partner_id in partner_ids:
        send_push_notification(partner_id, title, body, url, category)
