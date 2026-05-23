from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsCompanyAdmin
from core.mixins import get_client_ip
from .serializers import CompanySerializer, CompanyUpdateSerializer


class CompanyProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/company/ — view own company profile (any authenticated user)
    PATCH /api/v1/company/ — update company details (admin only)
    """

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsCompanyAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CompanyUpdateSerializer
        return CompanySerializer

    def get_object(self):
        return self.request.user.company

    def perform_update(self, serializer):
        instance = serializer.save()
        from apps.audit.tasks import create_audit_log_async
        create_audit_log_async.delay(
            company_id=str(self.request.user.company_id),
            user_id=str(self.request.user.id),
            action="update",
            resource_type="company",
            resource_id=str(instance.pk),
            resource_repr=str(instance),
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get("HTTP_USER_AGENT", ""),
        )
