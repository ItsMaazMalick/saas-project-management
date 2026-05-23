from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from apps.accounts.permissions import IsCompanyAdmin
from .filters import AuditLogFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    Read-only view of audit logs for the current company.
    Restricted to admins. Supports filtering by action, resource type, user, and date range.
    """

    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated, IsCompanyAdmin)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AuditLogFilter
    ordering_fields = ("timestamp",)
    ordering = ("-timestamp",)

    def get_queryset(self):
        return AuditLog.objects.filter(company=self.request.user.company)
