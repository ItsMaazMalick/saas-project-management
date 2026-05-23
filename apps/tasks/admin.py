from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "assigned_to", "due_date", "is_deleted")
    list_filter = ("status", "priority", "is_deleted", "company")
    search_fields = ("title", "description", "project__name", "assigned_to__email")
    readonly_fields = ("id", "created_at", "updated_at", "created_by")
    raw_id_fields = ("project", "assigned_to", "created_by")
