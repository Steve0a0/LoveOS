from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Create default Celery Beat periodic task schedules."

    def handle(self, *args, **options):
        daily, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.DAYS
        )

        tasks = [
            {
                "name": "Check upcoming important dates",
                "task": "core.check_upcoming_dates",
                "interval": daily,
            },
            {
                "name": "Send daily couple digest",
                "task": "core.send_daily_digest",
                "interval": daily,
            },
            {
                "name": "Expire old invites",
                "task": "core.expire_old_invites",
                "interval": daily,
            },
        ]

        for t in tasks:
            obj, created = PeriodicTask.objects.get_or_create(
                name=t["name"],
                defaults={"task": t["task"], "interval": t["interval"]},
            )
            status = "created" if created else "already exists"
            self.stdout.write(f"  {t['name']} — {status}")

        self.stdout.write(self.style.SUCCESS("Done."))
