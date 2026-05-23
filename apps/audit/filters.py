import django_filters
from .models import AuditLog, AuditAction


class AuditLogFilter(django_filters.FilterSet):
    action = django_filters.ChoiceFilter(choices=AuditAction.choices)
    resource_type = django_filters.CharFilter(lookup_expr="iexact")
    user_email = django_filters.CharFilter(lookup_expr="icontains")
    timestamp_after = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    timestamp_before = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ("action", "resource_type", "user_email")
