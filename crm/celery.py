import os
from celery import Celery

# Point Celery to Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "alx_backend_graphql_crm.settings")

app = Celery("crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
