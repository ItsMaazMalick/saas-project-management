from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Project, ProjectMember, ProjectStatus

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProjectMember
        fields = ("id", "user", "user_id", "joined_at")
        read_only_fields = ("id", "joined_at")


class ProjectListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    member_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "name", "description", "status", "owner_id", "owner_name",
            "member_count", "task_count", "start_date", "end_date", "created_at",
        )

    def get_member_count(self, obj):
        return obj.project_members.count()

    def get_task_count(self, obj):
        return obj.tasks.filter(is_deleted=False).count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "name", "description", "status", "owner", "members",
            "task_count", "start_date", "end_date", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_members(self, obj):
        return ProjectMemberSerializer(obj.project_members.select_related("user"), many=True).data

    def get_task_count(self, obj):
        return obj.tasks.filter(is_deleted=False).count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = (
            "id", "name", "description", "status", "owner",
            "member_ids", "start_date", "end_date",
        )
        read_only_fields = ("id",)

    def validate_owner(self, value):
        request = self.context["request"]
        if value and (value.company != request.user.company or value.is_deleted):
            raise serializers.ValidationError("Owner must be an active user in your company.")
        return value

    def validate_member_ids(self, value):
        request = self.context["request"]
        valid_ids = set(
            request.user.company.users.filter(id__in=value, is_deleted=False).values_list("id", flat=True)
        )
        invalid = [str(uid) for uid in value if uid not in valid_ids]
        if invalid:
            raise serializers.ValidationError(f"Users not found in your company: {invalid}")
        return value

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        project = super().create(validated_data)
        if member_ids:
            ProjectMember.objects.bulk_create(
                [ProjectMember(project=project, user_id=uid) for uid in member_ids],
                ignore_conflicts=True,
            )
        # Auto-add owner as member
        if project.owner_id:
            ProjectMember.objects.get_or_create(project=project, user_id=project.owner_id)
        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("name", "description", "status", "owner", "start_date", "end_date")

    def validate_owner(self, value):
        request = self.context["request"]
        if value and (value.company != request.user.company or value.is_deleted):
            raise serializers.ValidationError("Owner must be an active user in your company.")
        return value


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()

    def validate_user_id(self, value):
        request = self.context["request"]
        project = self.context["project"]
        if not request.user.company.users.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError("User not found in your company.")
        if ProjectMember.objects.filter(project=project, user_id=value).exists():
            raise serializers.ValidationError("User is already a member of this project.")
        return value
