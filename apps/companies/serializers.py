from rest_framework import serializers
from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id", "name", "slug", "domain", "description",
            "is_active", "user_count", "project_count", "created_at",
        )
        read_only_fields = ("id", "slug", "is_active", "created_at")

    def get_user_count(self, obj):
        return obj.users.filter(is_deleted=False, is_active=True).count()

    def get_project_count(self, obj):
        return obj.projects.filter(is_deleted=False).count()


class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("name", "domain", "description")
