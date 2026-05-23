from django.contrib import admin
from .models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    readonly_fields = ("joined_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "status", "owner", "is_deleted", "created_at")
    list_filter = ("status", "is_deleted", "company")
    search_fields = ("name", "company__name", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProjectMemberInline]
