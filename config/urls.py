from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/users/", include("apps.accounts.user_urls")),
    path("api/v1/company/", include("apps.companies.urls")),
    path("api/v1/projects/", include("apps.projects.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),
]
