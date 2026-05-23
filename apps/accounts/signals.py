# JWT authentication does not trigger Django's user_logged_in/user_logged_out signals
# because those signals require calling django.contrib.auth.login() which only happens
# in session-based auth. JWT login audit is handled explicitly in LoginView.post().
# This file is retained for session-based admin login logging only.

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


@receiver(user_logged_in)
def on_admin_login(sender, request, user, **kwargs):
    """Audit log for Django admin / session-based logins only."""
    from apps.audit.tasks import create_audit_log_async
    from core.mixins import get_client_ip

    create_audit_log_async.delay(
        company_id=str(user.company_id) if user.company_id else None,
        user_id=str(user.id),
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        resource_repr=user.email,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
