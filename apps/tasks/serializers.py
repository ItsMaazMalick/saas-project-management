from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from apps.projects.models import Project
from .models import Task, TaskPriority, TaskStatus


class TaskListSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "title", "status", "priority", "project_id", "project_name",
            "assigned_to_id", "assigned_to_name", "created_by_name",
            "due_date", "created_at",
        )


class TaskDetailSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "status", "priority",
            "project_id", "project_name", "assigned_to", "created_by",
            "due_date", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "created_by")


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "status", "priority",
            "project", "assigned_to", "due_date",
        )
        read_only_fields = ("id",)

    def validate_project(self, value):
        request = self.context["request"]
        if value.company != request.user.company or value.is_deleted:
            raise serializers.ValidationError("Project not found in your company.")
        return value

    def validate_assigned_to(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if value.company != request.user.company or value.is_deleted:
            raise serializers.ValidationError("User not found in your company.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        task = Task.objects.create(
            company=request.user.company,
            created_by=request.user,
            **validated_data,
        )

        if task.assigned_to:
            from .tasks import notify_task_assigned
            notify_task_assigned.delay(str(task.id))

        return task


class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ("title", "description", "status", "priority", "assigned_to", "due_date")

    def validate_assigned_to(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if value.company != request.user.company or value.is_deleted:
            raise serializers.ValidationError("User not found in your company.")
        return value

    def update(self, instance, validated_data):
        old_assignee = instance.assigned_to_id
        instance = super().update(instance, validated_data)
        new_assignee = instance.assigned_to_id

        if new_assignee and new_assignee != old_assignee:
            from .tasks import notify_task_assigned
            notify_task_assigned.delay(str(instance.id))

        return instance
