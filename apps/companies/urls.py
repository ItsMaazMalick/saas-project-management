from django.urls import path
from .views import CompanyProfileView

urlpatterns = [
    path("", CompanyProfileView.as_view(), name="company-profile"),
]
