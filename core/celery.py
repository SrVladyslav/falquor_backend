from __future__ import absolute_import, unicode_literals
import os

# from django.core.mail import send_mail
from celery import Celery
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "core.settings.dev")
)

worker = Celery("core")

redis_password = os.getenv("REDIS_PASSWORD", "place_your_default_secret_here")
worker.conf.broker_url = f"redis://:{redis_password}@redis:6379/0"
worker.conf.result_backend = f"redis://:{redis_password}@redis:6379/0"

worker.config_from_object("django.conf:settings", namespace="CELERY")

worker.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
