from django.conf import settings
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

logger = logging.getLogger(__name__)

from apps.accounts.account_lifecycle import (
    REACTIVATION_PROMPT_MESSAGE,
    build_reactivation_path,
)
from apps.accounts.models import EmailOTP, PendingSignup, User
from apps.accounts.presence import clear_user_presence
from apps.accounts.serializers import (
    AdminRegisterSerializer,
    AccountSettingsSerializer,
    ChangeEmailSerializer,
    ChangeMobileNumberSerializer,
    ChangePasswordSerializer,
    CompanySettingsOTPConfirmSerializer,
    CompanySettingsOTPRequestSerializer,
    CompanyRegistrationLookupSerializer,
    CorpersTokenObtainPairSerializer,
    CorpersTokenRefreshSerializer,
    CurrentUserSerializer,
    DeleteAccountSerializer,
    ForgotPasswordSerializer,
    OTPVerifySerializer,
    ProfileVisibilitySerializer,
    ReactivationResolveSerializer,
    RegisterSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    VerifyPasswordResetCodeSerializer,
)
from apps.accounts.services import consume_valid_otp
from apps.adminpanel.models import AdminRegistrationRequest
from apps.adminpanel.services import (
    get_primary_admin_user,
    send_admin_request_notification,
)
from apps.audit.services import log_audit_event


def _set_refresh_cookie(response: Response, refresh_token: str, max_age: int | None = None, remember: bool = False) -> Response:
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        max_age=max_age or settings.AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_REMEMBER_NAME,
        "true" if remember else "false",
        httponly=False,
        max_age=max_age or settings.AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )
    return response


def _clear_refresh_cookie(response: Response) -> Response:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_REMEMBER_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )
    return response


class RegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending_signup = serializer.save()
        payload = {
            "message": "Verification code sent. Complete email verification to finish creating your account.",
            "email": pending_signup.email,
            "role": pending_signup.role,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class AdminRegisterAPIView(GenericAPIView):
    serializer_class = AdminRegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class AdminRegisterVerifyAPIView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip()
        code = request.data.get("code", "").strip().upper()

        normalized_email = User.objects.normalize_email(email)
        pending_signup = PendingSignup.objects.filter(email=normalized_email).first()

        if not pending_signup or pending_signup.role != User.Role.ADMIN:
            return Response(
                {"email": ["No pending admin registration found for this email."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email__iexact=normalized_email).exists():
            return Response(
                {"email": ["Email already registered, please login to account."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = consume_valid_otp(email=normalized_email, code=code, purpose=EmailOTP.Purpose.SIGNUP)

        first_admin = get_primary_admin_user()
        admin_request = None
        if first_admin is None:
            with transaction.atomic():
                admin_user = User(
                    email=normalized_email,
                    role=User.Role.ADMIN,
                    email_verified=True,
                    is_active=True,
                    is_staff=True,
                )
                admin_user.password = pending_signup.password_hash
                admin_user.save()
                log_audit_event(
                    actor=admin_user,
                    action="auth.first_admin_registered",
                    target_type="user",
                    target_id=str(admin_user.id),
                    metadata={"email": admin_user.email, "bootstrap": True},
                )

            pending_signup.delete()
            EmailOTP.objects.filter(
                email=normalized_email, purpose=EmailOTP.Purpose.SIGNUP
            ).delete()

            return Response(
                {
                    "status": "created",
                    "message": "First admin account created successfully. Sign in to continue.",
                    "email": normalized_email,
                },
                status=status.HTTP_201_CREATED,
            )

        if first_admin is not None:
            with transaction.atomic():
                admin_request = AdminRegistrationRequest(
                    email=normalized_email,
                    password_hash=pending_signup.password_hash,
                    status=AdminRegistrationRequest.Status.PENDING,
                )
                admin_request.save()
                log_audit_event(
                    action="admin.registration_requested",
                    target_type="admin_registration_request",
                    target_id=str(admin_request.id),
                    metadata={"email": admin_request.email},
                )

            try:
                send_admin_request_notification(request=admin_request, admin_user=first_admin)
            except Exception:
                logger.exception(
                    "Unable to send admin registration request notification",
                    extra={"request_id": str(admin_request.id), "email": admin_request.email, "admin_email": first_admin.email},
                )
            else:
                admin_request.notification_sent_at = timezone.now()
                admin_request.save(update_fields=["notification_sent_at", "updated_at"])

        pending_signup.delete()
        EmailOTP.objects.filter(email=normalized_email, purpose=EmailOTP.Purpose.SIGNUP).delete()

        return Response(
            {
                "status": "pending",
                "message": "Admin access request submitted. An existing admin will review your request.",
                "email": normalized_email,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CompanyRegistrationLookupAPIView(GenericAPIView):
    serializer_class = CompanyRegistrationLookupSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "company_lookup"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        return Response(
            {
                "message": "Company registration number verified.",
                "data": company.to_response_payload(),
            }
        )


class VerifyEmailAPIView(GenericAPIView):
    serializer_class = OTPVerifySerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Email verification successful. Your account is ready.",
                "user": CurrentUserSerializer(user).data,
            }
        )


class ResendOTPAPIView(GenericAPIView):
    serializer_class = ResendOTPSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "If the account exists, a fresh OTP has been sent."})


class CorpersTokenObtainPairView(TokenObtainPairView):
    serializer_class = CorpersTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh_token = response.data.pop("refresh", None) if isinstance(response.data, dict) else None
        if response.status_code == status.HTTP_200_OK and refresh_token:
            raw_remember = request.data.get("remember_me")
            remember_me = raw_remember in {"true", "on", "True", "1", "yes", True}
            max_age = (
                settings.AUTH_REFRESH_COOKIE_REMEMBER_MAX_AGE
                if remember_me
                else settings.AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE
            )
            _set_refresh_cookie(response, refresh_token, max_age=max_age, remember=remember_me)
        return response


class CorpersTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CorpersTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        request_refresh_token = request.data.get("refresh") if hasattr(request, "data") else None
        cookie_refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not request_refresh_token and not cookie_refresh_token:
            return Response({"detail": "No refresh token provided."}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)
        refresh_token = response.data.pop("refresh", None) if isinstance(response.data, dict) else None
        if response.status_code == status.HTTP_200_OK and refresh_token:
            remember_cookie = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_REMEMBER_NAME)
            remember = remember_cookie in {"true", "True", "1", "yes"}
            max_age = (
                settings.AUTH_REFRESH_COOKIE_REMEMBER_MAX_AGE
                if remember
                else settings.AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE
            )
            _set_refresh_cookie(response, refresh_token, max_age=max_age, remember=remember)
        return response


class LogoutAPIView(GenericAPIView):
    def post(self, request, *args, **kwargs):
        clear_user_presence(user=request.user)
        response = Response({"message": "Signed out successfully."})
        return _clear_refresh_cookie(response)


class ForgotPasswordAPIView(GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_request"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "If the account exists, a reset code has been sent."})


class ResetPasswordAPIView(GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_complete"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset successful."})


class VerifyPasswordResetCodeAPIView(GenericAPIView):
    serializer_class = VerifyPasswordResetCodeSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_verify"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(
            {
                "message": "Reset code verified.",
                "reset_token": payload["reset_token"],
                "email": payload["user"].email if payload.get("user") else serializer.validated_data["email"],
            }
        )


class ReactivationResolveAPIView(GenericAPIView):
    serializer_class = ReactivationResolveSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(
            {
                "message": REACTIVATION_PROMPT_MESSAGE,
                "user": {
                    "email": user.email,
                    "role": user.role,
                },
                "billing_path": build_reactivation_path(token=serializer.validated_data["token"]),
            }
        )


class MeAPIView(RetrieveAPIView):
    serializer_class = CurrentUserSerializer

    def get_object(self):
        return self.request.user


class AccountSettingsAPIView(RetrieveAPIView):
    serializer_class = AccountSettingsSerializer

    def get_object(self):
        return self.request.user


class ProfileVisibilityAPIView(GenericAPIView):
    serializer_class = ProfileVisibilitySerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        paused = profile.directory_visibility_paused
        role_label = "Company" if request.user.role == "company" else "Corper"
        state_label = "paused" if paused else "active"
        return Response(
            {
                "message": f"{role_label} profile visibility is now {state_label}.",
                "profile_visibility_paused": paused,
            }
        )


class ChangePasswordAPIView(GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password updated successfully."})


class ChangeEmailAPIView(GenericAPIView):
    serializer_class = ChangeEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Email updated successfully.",
                "user": CurrentUserSerializer(user).data,
            }
        )


class ChangeMobileNumberAPIView(GenericAPIView):
    serializer_class = ChangeMobileNumberSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.save()
        return Response(
            {
                "message": "Mobile number updated successfully.",
                "mobile_number": mobile_number,
                "user": CurrentUserSerializer(request.user).data,
            }
        )


class DeleteAccountAPIView(GenericAPIView):
    serializer_class = DeleteAccountSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response({"message": "Account deleted successfully."})
        return _clear_refresh_cookie(response)


class CompanySettingsOTPRequestAPIView(GenericAPIView):
    serializer_class = CompanySettingsOTPRequestSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(
            {
                "message": "Verification code sent successfully.",
                "action": payload["action"],
                "target_email": payload["target_email"],
            }
        )


class CompanySettingsOTPConfirmAPIView(GenericAPIView):
    serializer_class = CompanySettingsOTPConfirmSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        response = Response(payload)
        if serializer.validated_data["action"] == CompanySettingsOTPConfirmSerializer.ACTION_DELETE_ACCOUNT:
            return _clear_refresh_cookie(response)
        return response
