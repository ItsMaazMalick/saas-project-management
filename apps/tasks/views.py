from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.accounts.models import UserRole
from apps.accounts.permissions import IsManagerOrAdmin, IsSameTenant
from core.mixins import TenantMixin, get_client_ip
from .models import Task
from .serializers import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
)
from .filters import TaskFilter


class TaskViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    Full CRUD for tasks.
    - Employees can only see tasks assigned to them or in their projects.
    - Status updates are allowed for assigned users.
    - All data is tenant-isolated.
    """

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = TaskFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "due_date", "priority", "status")
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "restore"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        if self.action == "create":
            return TaskCreateSerializer
        if self.action in ("update", "partial_update"):
            return TaskUpdateSerializer
        return TaskDetailSerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = (
            Task.objects.filter(company=user.company, is_deleted=False)
            .select_related("assigned_to", "created_by", "project", "company")
        )
        if user.role == UserRole.EMPLOYEE:
            base_qs = base_qs.filter(
                assigned_to=user
            ) | base_qs.filter(project__members=user)
            base_qs = base_qs.distinct()
        return base_qs

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log(self.request, "create", instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log(self.request, "update", instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        self._log(request, "delete", instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def restore(self, request, pk=None):
        instance = Task.all_objects.filter(
            company=request.user.company, pk=pk, is_deleted=True
        ).first()
        if not instance:
            return Response(
                {"detail": "Task not found or not deleted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        instance.restore()
        self._log(request, "restore", instance)
        return Response(TaskDetailSerializer(instance).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def deleted(self, request):
        tasks = Task.all_objects.filter(
            company=request.user.company, is_deleted=True
        ).select_related("assigned_to", "project")
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """Allow assigned employee to update their task status."""
        task = self.get_object()
        user = request.user

        if user.role == UserRole.EMPLOYEE and task.assigned_to != user:
            return Response(
                {"detail": "You can only update status of tasks assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")
        from .models import TaskStatus
        if new_status not in TaskStatus.values:
            return Response(
                {"detail": f"Invalid status. Choose from: {TaskStatus.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.status = new_status
        task.save(update_fields=["status", "updated_at"])
        self._log(request, "update", task)
        return Response(TaskDetailSerializer(task).data)

    def _log(self, request, action, instance):
        from apps.audit.tasks import create_audit_log_async
        create_audit_log_async.delay(
            company_id=str(request.user.company_id),
            user_id=str(request.user.id),
            action=action,
            resource_type="task",
            resource_id=str(instance.pk),
            resource_repr=str(instance),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
