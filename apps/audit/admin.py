from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "resource_type", "resource_repr", "user_email", "company", "ip_address", "timestamp")
    list_filter = ("action", "resource_type", "company")
    search_fields = ("user_email", "resource_repr", "resource_id")
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
