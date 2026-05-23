import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def create_audit_log_async(
    company_id,
    user_id,
    action,
    resource_type,
    resource_id="",
    resource_repr="",
    ip_address=None,
    user_agent="",
    extra_data=None,
):
    """Create an audit log entry asynchronously."""
    try:
        from apps.audit.models import AuditLog
        from apps.companies.models import Company
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = None
        user_email = ""
        company = None

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                user_email = user.email
            except User.DoesNotExist:
                pass

        if company_id:
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                pass

        AuditLog.objects.create(
            company=company,
            user=user,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_repr=resource_repr,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {},
        )
        logger.debug("Audit log created: %s on %s by %s", action, resource_type, user_email)
    except Exception as exc:
        logger.error("Failed to create audit log: %s", exc)


@shared_task
def send_daily_summary_emails():
    """Send daily activity summary to all company admins."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.audit.models import AuditLog
    from apps.companies.models import Company
    from django.contrib.auth import get_user_model
    from apps.accounts.models import UserRole

    User = get_user_model()
    yesterday = timezone.now() - timedelta(days=1)

    for company in Company.objects.filter(is_active=True):
        admins = User.objects.filter(
            company=company,
            role=UserRole.ADMIN,
            is_active=True,
            is_deleted=False,
        )
        if not admins.exists():
            continue

        logs = AuditLog.objects.filter(
            company=company,
            timestamp__gte=yesterday,
        ).order_by("-timestamp")[:50]

        if not logs.exists():
            continue

        summary_lines = [f"- {log.action.upper()} {log.resource_type} by {log.user_email}" for log in logs]
        summary = "\n".join(summary_lines)

        for admin in admins:
            send_mail(
                subject=f"Daily Activity Summary — {company.name}",
                message=(
                    f"Hi {admin.get_full_name()},\n\n"
                    f"Here is a summary of activity in {company.name} over the last 24 hours:\n\n"
                    f"{summary}\n\nBest regards,\nThe SaaS Platform Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True,
            )
            logger.info("Daily summary sent to %s for company %s", admin.email, company.name)
