import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def notify_project_member_added(self, project_id: str, user_id: str):
    try:
        from apps.projects.models import Project
        from django.contrib.auth import get_user_model
        User = get_user_model()

        project = Project.objects.select_related("company").get(id=project_id)
        user = User.objects.get(id=user_id)

        send_mail(
            subject=f"You've been added to project: {project.name}",
            message=(
                f"Hi {user.get_full_name()},\n\n"
                f"You have been added to the project '{project.name}' "
                f"in {project.company.name}.\n\n"
                f"Log in to start collaborating.\n\nBest regards,\nThe Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Project member notification sent to %s for project %s", user.email, project_id)
    except Exception as exc:
        logger.error("Failed to send project member notification: %s", exc)
        raise self.retry(exc=exc, countdown=60)
