from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.mixins import AuditLogMixin, get_client_ip
from .models import UserRole
from .permissions import IsCompanyAdmin, IsManagerOrAdmin
from .serializers import (
    ChangePasswordSerializer,
    CompanyRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class RegisterCompanyView(generics.CreateAPIView):
    """Register a new company with an admin user account."""

    serializer_class = CompanyRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Company registered successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """JWT login — returns access + refresh tokens with user info."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_data = response.data.get("user", {})
            user_id = user_data.get("id")
            company_id = user_data.get("company_id")
            if user_id:
                from apps.audit.tasks import create_audit_log_async
                create_audit_log_async.delay(
                    company_id=company_id,
                    user_id=user_id,
                    action="login",
                    resource_type="user",
                    resource_id=user_id,
                    resource_repr=user_data.get("email", ""),
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
        return response


class LogoutView(generics.GenericAPIView):
    """Blacklist the refresh token to invalidate the session."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            from apps.audit.tasks import create_audit_log_async
            create_audit_log_async.delay(
                company_id=str(request.user.company_id) if request.user.company_id else None,
                user_id=str(request.user.id),
                action="logout",
                resource_type="user",
                resource_id=str(request.user.id),
                resource_repr=str(request.user),
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(generics.RetrieveUpdateAPIView):
    """Get or update the currently authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(generics.GenericAPIView):
    """Change password for the authenticated user."""

    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"message": "Password changed successfully."})


class UserViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """
    Admin-only CRUD for users within the same company.
    Employees are isolated — they cannot see users from other companies.
    """

    audit_resource_type = "user"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsCompanyAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        return User.objects.filter(
            company=self.request.user.company,
            is_deleted=False,
        ).order_by("first_name", "last_name")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save(update_fields=["is_deleted", "deleted_at", "is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        user = User.objects.filter(
            company=request.user.company, pk=pk, is_deleted=True
        ).first()
        if not user:
            return Response(
                {"detail": "User not found or not deleted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        user.is_deleted = False
        user.deleted_at = None
        user.is_active = True
        user.save(update_fields=["is_deleted", "deleted_at", "is_active"])
        return Response(UserSerializer(user).data)

    @action(detail=False, methods=["get"])
    def deleted(self, request):
        users = User.objects.filter(company=request.user.company, is_deleted=True)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
