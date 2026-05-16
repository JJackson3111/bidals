from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer
from apps.audit.models import AuditAction, AuditLog
from apps.audit.security import (
    audit_security_event,
    check_security_rate_limit,
    client_ip,
    rate_limited_response,
    request_audit_metadata,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        rate_limit = check_security_rate_limit(
            request,
            scope="registration",
            identifier=client_ip(request),
            setting_name="RATE_LIMIT_REGISTRATION",
            default_rate="5/minute",
        )
        if not rate_limit.allowed:
            return rate_limited_response(rate_limit)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        AuditLog.objects.create(
            actor=user,
            action=AuditAction.USER_REGISTERED,
            entity_type="user",
            entity_id=str(user.id),
            metadata=request_audit_metadata(
                request,
                {"username": user.username, "role": user.role},
            ),
        )

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        login_identifier = str(request.data.get("username", "")).strip().lower()[:150]
        rate_limit = check_security_rate_limit(
            request,
            scope="login",
            identifier=f"{client_ip(request)}:{login_identifier}",
            setting_name="RATE_LIMIT_LOGIN",
            default_rate="5/minute",
        )
        if not rate_limit.allowed:
            return rate_limited_response(rate_limit)

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            audit_security_event(
                request=request,
                action=AuditAction.LOGIN_FAILED,
                entity_type="auth",
                entity_id="login",
                metadata={"login_identifier": login_identifier, "reason": "invalid_credentials"},
            )
            raise

        user = serializer.user
        audit_security_event(
            request=request,
            actor=user,
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="user",
            entity_id=str(user.id),
            metadata={"username": user.username, "role": user.role},
        )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        actor = None
        try:
            token = RefreshToken(request.data.get("refresh", ""))
            user_id = token.get("user_id")
            actor = User.objects.filter(pk=user_id).first()
        except Exception:
            actor = None

        response = super().post(request, *args, **kwargs)
        audit_security_event(
            request=request,
            actor=actor,
            action=AuditAction.TOKEN_REFRESH,
            entity_type="user" if actor else "auth",
            entity_id=str(actor.id) if actor else "refresh",
            metadata={"rotated": bool(response.data.get("refresh")) if hasattr(response, "data") else False},
        )
        return response


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "A refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh token is invalid or already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audit_security_event(
            request=request,
            actor=request.user,
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=str(request.user.id),
            metadata={"username": request.user.username},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)
