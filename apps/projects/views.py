from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.accounts.permissions import IsManagerOrAdmin, IsSameTenant
from core.mixins import AuditLogMixin, TenantMixin, get_client_ip
from .models import Project, ProjectMember
from .serializers import (
    AddMemberSerializer,
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
    ProjectUpdateSerializer,
)

User = get_user_model()


class ProjectViewSet(AuditLogMixin, TenantMixin, viewsets.ModelViewSet):
    """
    Full CRUD for projects.
    - Listing is filtered by role: employees see only their assigned projects.
    - Creating/editing requires manager or admin role.
    - All operations are scoped to the current tenant.
    """

    audit_resource_type = "project"

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "restore"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsSameTenant()]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        if self.action == "create":
            return ProjectCreateSerializer
        if self.action in ("update", "partial_update"):
            return ProjectUpdateSerializer
        return ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = (
            Project.objects.filter(company=user.company, is_deleted=False)
            .select_related("owner", "company")
            .prefetch_related("project_members__user")
        )
        if user.role == UserRole.EMPLOYEE:
            base_qs = base_qs.filter(members=user)
        return base_qs

    def perform_create(self, serializer):
        # Default owner to current user only when not explicitly provided in request
        owner = serializer.validated_data.get("owner") or self.request.user
        instance = serializer.save(
            company=self.request.user.company,
            owner=owner,
        )
        self._create_audit_log(self.request, "create", instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._create_audit_log(self.request, "update", instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        self._create_audit_log(request, "delete", instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def restore(self, request, pk=None):
        instance = Project.all_objects.filter(
            company=request.user.company, pk=pk, is_deleted=True
        ).first()
        if not instance:
            return Response(
                {"detail": "Project not found or not deleted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        instance.restore()
        self._create_audit_log(request, "restore", instance)
        return Response(ProjectDetailSerializer(instance).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def deleted(self, request):
        projects = Project.all_objects.filter(
            company=request.user.company, is_deleted=True
        ).select_related("owner")
        serializer = ProjectListSerializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """
        GET  /projects/{id}/members/ — list project members (any authenticated user)
        POST /projects/{id}/members/ — add member to project (manager/admin only)
        """
        project = self.get_object()

        if request.method == "GET":
            qs = project.project_members.select_related("user")
            serializer = ProjectMemberSerializer(qs, many=True)
            return Response(serializer.data)

        # POST — add member
        if not request.user.is_manager_or_admin:
            return Response(
                {"detail": "You do not have permission to add members."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AddMemberSerializer(
            data=request.data,
            context={"request": request, "project": project},
        )
        serializer.is_valid(raise_exception=True)
        member = ProjectMember.objects.create(
            project=project,
            user_id=serializer.validated_data["user_id"],
        )
        from .tasks import notify_project_member_added
        notify_project_member_added.delay(str(project.id), str(member.user_id))
        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="members/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsManagerOrAdmin],
    )
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        deleted, _ = ProjectMember.objects.filter(project=project, user_id=user_id).delete()
        if not deleted:
            return Response(
                {"detail": "Member not found in this project."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _create_audit_log(self, request, action, instance):
        from apps.audit.tasks import create_audit_log_async
        create_audit_log_async.delay(
            company_id=str(request.user.company_id),
            user_id=str(request.user.id),
            action=action,
            resource_type="project",
            resource_id=str(instance.pk),
            resource_repr=str(instance),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
