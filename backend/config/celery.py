import os
import sys

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("loveos")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Windows doesn't support the prefork pool — use solo instead.
if sys.platform == "win32":
    app.conf.worker_pool = "solo"
