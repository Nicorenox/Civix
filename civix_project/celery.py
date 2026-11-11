import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "civix_project.settings")
app = Celery("civix")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
