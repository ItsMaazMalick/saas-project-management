import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("saas_project_management")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_schedule = {
    "send-daily-summary-emails": {
        "task": "apps.audit.tasks.send_daily_summary_emails",
        "schedule": crontab(hour=8, minute=0),
    },
}
