from rest_framework.response import Response
from rest_framework import status


class TenantMixin:
    """
    Enforces tenant isolation at the view level.
    All querysets are automatically scoped to the authenticated user's company.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SoftDeleteMixin:
    """Adds restore action and overrides destroy to soft delete."""

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        self._log_action(request, instance, "delete")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def restore(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_deleted:
            return Response(
                {"detail": "This record is not deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.restore()
        self._log_action(request, instance, "restore")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def _log_action(self, request, instance, action):
        """Override in subclasses to add audit logging."""
        pass


class AuditLogMixin:
    """Triggers audit log creation after create/update/delete actions."""

    audit_resource_type = None

    def get_audit_resource_type(self):
        return self.audit_resource_type or self.queryset.model.__name__.lower()

    def perform_create(self, serializer):
        instance = serializer.save()
        self._create_audit_log(self.request, "create", instance)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        self._create_audit_log(self.request, "update", instance)
        return instance

    def _create_audit_log(self, request, action, instance):
        from apps.audit.tasks import create_audit_log_async
        create_audit_log_async.delay(
            company_id=str(request.user.company_id),
            user_id=str(request.user.id),
            action=action,
            resource_type=self.get_audit_resource_type(),
            resource_id=str(instance.pk),
            resource_repr=str(instance),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
