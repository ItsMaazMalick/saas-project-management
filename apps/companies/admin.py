from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "domain", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "domain")
    readonly_fields = ("id", "slug", "created_at", "updated_at")
