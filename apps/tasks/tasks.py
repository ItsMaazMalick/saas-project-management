import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def notify_task_assigned(self, task_id: str):
    try:
        from apps.tasks.models import Task
        task = Task.objects.select_related(
            "assigned_to", "project", "created_by", "company"
        ).get(id=task_id)

        if not task.assigned_to:
            return

        send_mail(
            subject=f"Task assigned: {task.title}",
            message=(
                f"Hi {task.assigned_to.get_full_name()},\n\n"
                f"You have been assigned a new task:\n"
                f"  Title: {task.title}\n"
                f"  Project: {task.project.name}\n"
                f"  Priority: {task.get_priority_display()}\n"
                f"  Due Date: {task.due_date or 'Not set'}\n\n"
                f"Log in to view full details.\n\nBest regards,\nThe Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[task.assigned_to.email],
            fail_silently=False,
        )
        logger.info("Task assignment notification sent to %s for task %s", task.assigned_to.email, task_id)
    except Exception as exc:
        logger.error("Failed to send task assignment notification: %s", exc)
        raise self.retry(exc=exc, countdown=60)
