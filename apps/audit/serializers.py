from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id", "user_email", "action", "resource_type",
            "resource_id", "resource_repr", "ip_address", "timestamp",
        )
        read_only_fields = fields
