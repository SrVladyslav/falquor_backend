from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from dotenv import load_dotenv
from django.conf import settings
from kombu import Exchange, Queue

load_dotenv()

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "core.settings.dev")
)

# Crear una nueva instancia para el worker de correos electrónicos
email_worker = Celery("core.celery_email_broker")

# Usando RabbitMQ para este worker específico
email_worker.conf.broker_url = os.getenv(
    "EMAIL_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"
)

# Configurar este worker para usar la cola de correos
email_worker.conf.task_queues = (
    Queue("emails", Exchange("emails"), routing_key="emails"),
)

email_worker.config_from_object("django.conf:settings", namespace="CELERY")
email_worker.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
