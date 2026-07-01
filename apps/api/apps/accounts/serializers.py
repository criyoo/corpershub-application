from __future__ import annotations

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from apps.accounts.account_lifecycle import (
    REACTIVATION_PROMPT_MESSAGE,
    build_reactivation_path,
    deactivate_expired_corper_account,
    get_reactivation_user,
    issue_reactivation_token,
)
from apps.accounts.models import EmailOTP, PendingSignup, User
from apps.accounts.services import (
    archive_deleted_user,
    complete_signup_verification,
    consume_valid_otp,
    create_or_update_pending_signup,
    consume_company_settings_otp,
    deleted_account_email_exists,
    get_password_reset_otp_from_token,
    get_valid_otp,
    issue_company_settings_otp,
    issue_password_reset_otp,
    issue_password_reset_verification_token,
    issue_signup_otp,
    prune_expired_pending_signups,
    validate_company_registration_email,
)
from apps.adminpanel.models import AdminRegistrationRequest
from apps.adminpanel.services import (
    get_primary_admin_user,
    send_admin_request_notification,
)
from apps.audit.services import log_audit_event
from apps.common.validators import validate_nigerian_mobile_number
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import (
    COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
    is_valid_company_registration_number,
    lookup_company_registration_number,
    normalize_company_registration_number,
)
from apps.companies.services import ensure_company_profile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import UserSubscription


class CompanyRegistrationNumberValidationMixin:
    def validate_company_registration_number(self, value):
        normalized = normalize_company_registration_number(value)
        if not normalized:
            raise serializers.ValidationError("Company registration number is required.")
        if not is_valid_company_registration_number(normalized):
            raise serializers.ValidationError(COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE)
        return normalized


class CompanyRegistrationLookupSerializer(CompanyRegistrationNumberValidationMixin, serializers.Serializer):
    company_registration_number = serializers.CharField(max_length=120)

    def create(self, validated_data):
        return lookup_company_registration_number(validated_data["company_registration_number"])


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[
            (User.Role.COMPANY, User.Role.COMPANY.label),
            (User.Role.CORPER, User.Role.CORPER.label),
        ]
    )
    subscription_plan_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_email(self, value):
        email = User.objects.normalize_email(value).strip()
        prune_expired_pending_signups(email=email)
        if deleted_account_email_exists(email):
            raise serializers.ValidationError(
                "This email is linked to a previously deleted account. Contact support if you need it restored."
            )
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user and existing_user.email_verified:
            raise serializers.ValidationError("An account with this email already exists.")
        if existing_user and not existing_user.email_verified:
            raise serializers.ValidationError("This email already belongs to an unverified account.")
        if PendingSignup.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("This email already belongs to an unverified account.")
        return email

    def validate(self, attrs):
        if attrs["role"] == User.Role.COMPANY:
            validate_company_registration_email(attrs["email"])
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        pending_signup = create_or_update_pending_signup(**validated_data)
        issue_signup_otp(
            email=pending_signup.email,
            target_type="pending_signup",
            target_id=str(pending_signup.id),
            metadata={"role": pending_signup.role},
        )
        log_audit_event(
            action="auth.signup_pending",
            target_type="pending_signup",
            target_id=str(pending_signup.id),
            metadata={"email": pending_signup.email, "role": pending_signup.role},
        )
        return pending_signup


class AdminRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        email = User.objects.normalize_email(value).strip()
        if deleted_account_email_exists(email):
            raise serializers.ValidationError(
                "This email is linked to a previously deleted account. Contact support if you need it restored."
            )
        return email

    def create(self, validated_data):
        pending_signup = create_or_update_pending_signup(
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Role.ADMIN,
        )
        issue_signup_otp(
            email=pending_signup.email,
            target_type="pending_signup",
            target_id=str(pending_signup.id),
            metadata={"role": User.Role.ADMIN},
        )
        log_audit_event(
            action="auth.admin_signup_pending",
            target_type="pending_signup",
            target_id=str(pending_signup.id),
            metadata={"email": pending_signup.email, "role": User.Role.ADMIN},
        )
        return {
            "status": "otp_sent",
            "message": "Verification code sent. Complete email verification to submit your admin access request.",
            "email": pending_signup.email,
        }


class AdminOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        return value.strip().upper()

    def validate_email(self, value):
        return User.objects.normalize_email(value).strip()

    def save(self, **kwargs):
        email = self.validated_data["email"]
        code = self.validated_data["code"]

        pending_signup = PendingSignup.objects.filter(email=email).first()
        if not pending_signup or pending_signup.role != User.Role.ADMIN:
            raise serializers.ValidationError({"email": ["No pending admin registration found for this email."]})

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": ["Email already registered, please login to account."]})

        consume_valid_otp(email=email, code=code, purpose=EmailOTP.Purpose.SIGNUP)

        first_admin = get_primary_admin_user()
        admin_request = None
        if first_admin is None:
            user = User(
                email=email,
                role=User.Role.ADMIN,
                email_verified=True,
                is_active=True,
                is_staff=True,
            )
            user.password = pending_signup.password_hash
            user.save()
            log_audit_event(
                actor=user,
                action="auth.first_admin_registered",
                target_type="user",
                target_id=str(user.id),
                metadata={"email": user.email, "bootstrap": True},
            )
            pending_signup.delete()
            EmailOTP.objects.filter(email=email, purpose=EmailOTP.Purpose.SIGNUP).delete()
            return {
                "status": "created",
                "message": "First admin account created successfully. Sign in to continue.",
                "email": email,
            }

        if first_admin is not None:
            admin_request = AdminRegistrationRequest(
                email=email,
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
                import logging

                logger = logging.getLogger(__name__)
                logger.exception(
                    "Unable to send admin registration request notification",
                    extra={
                        "request_id": str(admin_request.id),
                        "email": admin_request.email,
                        "admin_email": first_admin.email,
                    },
                )
            else:
                from django.utils import timezone

                admin_request.notification_sent_at = timezone.now()
                admin_request.save(update_fields=["notification_sent_at", "updated_at"])

        pending_signup.delete()
        EmailOTP.objects.filter(email=email, purpose=EmailOTP.Purpose.SIGNUP).delete()

        return {
            "status": "pending",
            "message": "Admin access request submitted. An existing admin will review your request.",
            "email": email,
        }


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        return value.strip().upper()

    def save(self, **kwargs):
        return complete_signup_verification(
            email=self.validated_data["email"],
            code=self.validated_data["code"],
        )


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def save(self, **kwargs):
        email = self.validated_data["email"]
        prune_expired_pending_signups(email=email)
        pending_signup = PendingSignup.objects.filter(email=email).first()
        if pending_signup:
            return issue_signup_otp(
                email=pending_signup.email,
                target_type="pending_signup",
                target_id=str(pending_signup.id),
                metadata={"role": pending_signup.role},
            )
        user = User.objects.filter(email=email, email_verified=False).first()
        if user:
            return issue_signup_otp(
                email=user.email,
                user=user,
                target_type="user",
                target_id=str(user.id),
                metadata={"role": user.role},
            )
        return None


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        user = User.objects.filter(email=self.validated_data["email"]).first()
        if user:
            issue_password_reset_otp(user=user)
        return user


class VerifyPasswordResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        return value.strip().upper()

    def save(self, **kwargs):
        otp = get_valid_otp(
            email=self.validated_data["email"],
            code=self.validated_data["code"],
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
        )
        otp.mark_verified()
        token = issue_password_reset_verification_token(otp=otp)
        log_audit_event(
            actor=otp.user,
            action="auth.password_reset_code_verified",
            target_type="user",
            target_id=str(otp.user.id) if otp.user else "",
        )
        return {"reset_token": token, "user": otp.user}


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    code = serializers.CharField(min_length=6, max_length=6, required=False, allow_blank=False)
    reset_token = serializers.CharField(required=False, allow_blank=False)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        has_reset_token = bool(attrs.get("reset_token"))
        has_code = bool(attrs.get("code"))
        has_email = bool(attrs.get("email"))

        if has_reset_token:
            return attrs

        if not has_code or not has_email:
            raise serializers.ValidationError(
                {"detail": "Provide either a verified reset token or both email and reset code."}
            )
        return attrs

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def save(self, **kwargs):
        reset_token = self.validated_data.get("reset_token")
        if reset_token:
            otp = get_password_reset_otp_from_token(token=reset_token)
        else:
            otp = get_valid_otp(
                email=self.validated_data["email"],
                code=self.validated_data["code"],
                purpose=EmailOTP.Purpose.PASSWORD_RESET,
            )
        user = otp.user
        new_password = self.validated_data["new_password"]
        if user and user.check_password(new_password):
            raise serializers.ValidationError(
                {"new_password": ["New password must be different from your current password."]}
            )
        if reset_token:
            otp.mark_consumed()
        else:
            otp.mark_verified()
            otp.mark_consumed()
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        log_audit_event(
            actor=user,
            action="auth.password_reset_completed",
            target_type="user",
            target_id=str(user.id),
        )
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    profile_id = serializers.SerializerMethodField()
    profile_completed = serializers.BooleanField(read_only=True)
    profile_path = serializers.SerializerMethodField()
    company_verification_status = serializers.SerializerMethodField()
    needs_subscription_selection = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "email_verified",
            "is_active",
            "created_at",
            "profile_id",
            "profile_completed",
            "profile_path",
            "company_verification_status",
            "needs_subscription_selection",
        )

    def get_profile_id(self, obj):
        if obj.role == User.Role.COMPANY and hasattr(obj, "company_profile"):
            return obj.company_profile.id
        if obj.role == User.Role.CORPER and hasattr(obj, "corper_profile"):
            return obj.corper_profile.id
        return None

    def get_profile_path(self, obj):
        if obj.role == User.Role.COMPANY:
            if hasattr(obj, "company_profile"):
                return obj.company_profile.next_profile_path
            return "/company/verification"
        if obj.role == User.Role.CORPER:
            if hasattr(obj, "corper_profile"):
                return obj.corper_profile.next_profile_path
            return "/corper/verification"
        return "/admin/overview"

    def get_company_verification_status(self, obj):
        if obj.role == User.Role.COMPANY and hasattr(obj, "company_profile"):
            return obj.company_profile.verification_status
        if obj.role == User.Role.COMPANY:
            return CompanyProfile.VerificationStatus.UNSUBMITTED
        return None

    def get_needs_subscription_selection(self, obj):
        if obj.role != User.Role.CORPER:
            return False
        return not UserSubscription.objects.filter(user=obj).exists()


class CorpersTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email_verified"] = user.email_verified
        return token

    def validate(self, attrs):
        email = attrs.get(self.username_field)
        if email:
            prune_expired_pending_signups(email=email)
        if email and PendingSignup.objects.filter(email=User.objects.normalize_email(email)).exists():
            raise serializers.ValidationError("Please verify your email before signing in.")
        user = None
        if email:
            user = User.objects.filter(email=User.objects.normalize_email(email)).first()
            if user:
                deactivate_expired_corper_account(user=user)
                user.refresh_from_db()
                if (
                    user.role == User.Role.CORPER
                    and not user.is_active
                    and user.deactivation_reason == User.DeactivationReason.AUTO_EXPIRED_13_MONTHS
                    and user.check_password(attrs["password"])
                ):
                    reactivation_token = issue_reactivation_token(user=user)
                    raise serializers.ValidationError(
                        {
                            "detail": REACTIVATION_PROMPT_MESSAGE,
                            "code": "reactivation_required",
                            "reactivation": {
                                "email": user.email,
                                "reactivation_token": reactivation_token,
                                "billing_path": build_reactivation_path(token=reactivation_token),
                            },
                        }
                    )
        data = super().validate(attrs)
        if not self.user.email_verified:
            raise serializers.ValidationError("Please verify your email before signing in.")
        data["user"] = CurrentUserSerializer(self.user).data
        return data


class CorpersTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        if not attrs.get("refresh"):
            request = self.context.get("request")
            refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME) if request else None
            if refresh_token:
                attrs = {
                    **attrs,
                    "refresh": refresh_token,
                }
            else:
                raise serializers.ValidationError({"detail": "No refresh token provided."})
        return super().validate(attrs)


class ReactivationResolveSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        attrs["user"] = get_reactivation_user(token=attrs["token"])
        return attrs


class AccountSettingsSerializer(serializers.ModelSerializer):
    mobile_number = serializers.SerializerMethodField()
    profile_path = serializers.SerializerMethodField()
    profile_visibility_paused = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "role",
            "mobile_number",
            "profile_completed",
            "profile_path",
            "profile_visibility_paused",
        )

    def get_mobile_number(self, obj):
        if obj.role == User.Role.COMPANY:
            return ensure_company_profile(obj).contact_phone
        if obj.role == User.Role.CORPER:
            return ensure_corper_profile(obj).mobile_number
        return ""

    def get_profile_path(self, obj):
        if obj.role == User.Role.COMPANY:
            if hasattr(obj, "company_profile"):
                return obj.company_profile.next_profile_path
            return "/company/verification"
        if obj.role == User.Role.CORPER:
            if hasattr(obj, "corper_profile"):
                return obj.corper_profile.next_profile_path
            return "/corper/verification"
        return "/admin/overview"

    def get_profile_visibility_paused(self, obj):
        if obj.role == User.Role.COMPANY:
            return ensure_company_profile(obj).directory_visibility_paused
        if obj.role == User.Role.CORPER:
            return ensure_corper_profile(obj).directory_visibility_paused
        return False


class ProfileVisibilitySerializer(serializers.Serializer):
    profile_visibility_paused = serializers.BooleanField()

    def save(self, **kwargs):
        user = self.context["request"].user
        paused = self.validated_data["profile_visibility_paused"]

        if user.role == User.Role.COMPANY:
            profile = ensure_company_profile(user)
        elif user.role == User.Role.CORPER:
            profile = ensure_corper_profile(user)
        else:
            raise serializers.ValidationError(
                {"detail": "Only corper and company accounts can update profile visibility."}
            )

        profile.directory_visibility_paused = paused
        profile.save(update_fields=["directory_visibility_paused", "updated_at"])
        return profile


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        user = self.context["request"].user
        try:
            validate_password(value, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        if user.check_password(value):
            raise serializers.ValidationError("New password must be different from your current password.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        log_audit_event(
            actor=user,
            action="auth.password_changed",
            target_type="user",
            target_id=str(user.id),
        )
        return user


class ChangeEmailSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_email = serializers.EmailField()

    def validate_current_password(self, value):
        user = self.context["request"].user
        if user.role == User.Role.COMPANY:
            raise serializers.ValidationError(
                "Company accounts must verify this action with an email OTP from the settings page."
            )
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_email(self, value):
        user = self.context["request"].user
        email = User.objects.normalize_email(value)
        if email == user.email:
            raise serializers.ValidationError("Enter a different email address.")
        if deleted_account_email_exists(email):
            raise serializers.ValidationError(
                "This email is linked to a previously deleted account. Contact support if you need it restored."
            )
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def save(self, **kwargs):
        user = self.context["request"].user
        previous_email = user.email
        user.email = self.validated_data["new_email"]
        user.save(update_fields=["email", "updated_at"])
        log_audit_event(
            actor=user,
            action="auth.email_changed",
            target_type="user",
            target_id=str(user.id),
            metadata={"previous_email": previous_email, "new_email": user.email},
        )
        return user


class ChangeMobileNumberSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    mobile_number = serializers.CharField(max_length=20)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if user.role == User.Role.COMPANY:
            raise serializers.ValidationError(
                "Company accounts must verify this action with an email OTP from the settings page."
            )
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_mobile_number(self, value):
        user = self.context["request"].user
        return validate_nigerian_mobile_number(
            value,
            field_label="Contact phone" if user.role == User.Role.COMPANY else "Mobile number",
            require_international_format=user.role == User.Role.CORPER,
        )

    def save(self, **kwargs):
        user = self.context["request"].user
        mobile_number = self.validated_data["mobile_number"]

        if user.role == User.Role.COMPANY:
            profile = ensure_company_profile(user)
            profile.contact_phone = mobile_number
            profile.save(update_fields=["contact_phone", "updated_at"])
        elif user.role == User.Role.CORPER:
            profile = ensure_corper_profile(user)
            profile.mobile_number = mobile_number
            profile.save(update_fields=["mobile_number", "updated_at"])
        else:
            raise serializers.ValidationError("Admins do not have a mobile number setting.")

        log_audit_event(
            actor=user,
            action="auth.mobile_number_changed",
            target_type="user",
            target_id=str(user.id),
            metadata={"role": user.role},
        )
        return mobile_number


class DeleteAccountSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if user.role == User.Role.COMPANY:
            raise serializers.ValidationError(
                "Company accounts must verify this action with an email OTP from the settings page."
            )
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        archived_record = archive_deleted_user(user=user)
        log_audit_event(
            actor=user,
            action="auth.account_deleted",
            target_type="user",
            target_id=str(user.id),
            metadata={"email": archived_record.email, "role": user.role},
        )
        return None


class CompanySettingsOTPRequestSerializer(serializers.Serializer):
    ACTION_CHANGE_PASSWORD = "change_password"
    ACTION_CHANGE_EMAIL = "change_email"
    ACTION_CHANGE_MOBILE_NUMBER = "change_mobile_number"
    ACTION_DELETE_ACCOUNT = "delete_account"

    action = serializers.ChoiceField(
        choices=[
            ACTION_CHANGE_PASSWORD,
            ACTION_CHANGE_EMAIL,
            ACTION_CHANGE_MOBILE_NUMBER,
            ACTION_DELETE_ACCOUNT,
        ]
    )
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    new_password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=False)
    new_email = serializers.EmailField(required=False)
    mobile_number = serializers.CharField(max_length=20, required=False, allow_blank=False)

    default_error_messages = {
        "company_only": "This OTP-secured settings flow is available for company accounts only.",
    }

    def validate_current_password(self, value):
        user = self.context["request"].user
        if user.role != User.Role.COMPANY:
            raise serializers.ValidationError(self.error_messages["company_only"])
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = self.context["request"].user
        action = attrs["action"]

        if user.role != User.Role.COMPANY:
            raise serializers.ValidationError({"detail": self.error_messages["company_only"]})

        target_email = user.email

        if action == self.ACTION_CHANGE_PASSWORD:
            new_password = attrs.get("new_password")
            if not new_password:
                raise serializers.ValidationError({"new_password": ["This field is required."]})
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
            if user.check_password(new_password):
                raise serializers.ValidationError(
                    {"new_password": ["New password must be different from your current password."]}
                )
        else:
            current_password = attrs.get("current_password")
            if not current_password:
                raise serializers.ValidationError({"current_password": ["This field is required."]})

        if action == self.ACTION_CHANGE_EMAIL:
            new_email = attrs.get("new_email")
            if not new_email:
                raise serializers.ValidationError({"new_email": ["This field is required."]})
            normalized_email = User.objects.normalize_email(new_email)
            if normalized_email == user.email:
                raise serializers.ValidationError({"new_email": ["Enter a different email address."]})
            if deleted_account_email_exists(normalized_email):
                raise serializers.ValidationError(
                    {
                        "new_email": [
                            "This email is linked to a previously deleted account. Contact support if you need it restored."
                        ]
                    }
                )
            if User.objects.filter(email=normalized_email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({"new_email": ["An account with this email already exists."]})
            attrs["new_email"] = normalized_email
            target_email = normalized_email
        elif action == self.ACTION_CHANGE_MOBILE_NUMBER:
            mobile_number = attrs.get("mobile_number")
            if not mobile_number:
                raise serializers.ValidationError({"mobile_number": ["This field is required."]})
            attrs["mobile_number"] = validate_nigerian_mobile_number(
                mobile_number,
                field_label="Contact phone",
                require_international_format=False,
            )

        attrs["target_email"] = target_email
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        issue_company_settings_otp(
            user=user,
            action=self.validated_data["action"],
            email=self.validated_data["target_email"],
        )
        return {
            "target_email": self.validated_data["target_email"],
            "action": self.validated_data["action"],
        }


class CompanySettingsOTPConfirmSerializer(CompanySettingsOTPRequestSerializer):
    otp_code = serializers.CharField(min_length=6, max_length=6)

    def validate_otp_code(self, value):
        return value.strip().upper()

    def save(self, **kwargs):
        user = self.context["request"].user
        action = self.validated_data["action"]
        target_email = self.validated_data["target_email"]
        consume_company_settings_otp(
            user=user,
            action=action,
            email=target_email,
            code=self.validated_data["otp_code"],
        )

        if action == self.ACTION_CHANGE_PASSWORD:
            user.set_password(self.validated_data["new_password"])
            user.save(update_fields=["password", "updated_at"])
            log_audit_event(
                actor=user,
                action="auth.password_changed",
                target_type="user",
                target_id=str(user.id),
            )
            return {"message": "Password updated successfully."}

        if action == self.ACTION_CHANGE_EMAIL:
            previous_email = user.email
            user.email = self.validated_data["new_email"]
            user.save(update_fields=["email", "updated_at"])
            log_audit_event(
                actor=user,
                action="auth.email_changed",
                target_type="user",
                target_id=str(user.id),
                metadata={"previous_email": previous_email, "new_email": user.email},
            )
            return {
                "message": "Email updated successfully.",
                "user": CurrentUserSerializer(user).data,
            }

        if action == self.ACTION_CHANGE_MOBILE_NUMBER:
            profile = ensure_company_profile(user)
            profile.contact_phone = self.validated_data["mobile_number"]
            profile.save(update_fields=["contact_phone", "updated_at"])
            log_audit_event(
                actor=user,
                action="auth.mobile_number_changed",
                target_type="user",
                target_id=str(user.id),
                metadata={"role": user.role},
            )
            return {
                "message": "Mobile number updated successfully.",
                "mobile_number": profile.contact_phone,
                "user": CurrentUserSerializer(user).data,
            }

        archived_record = archive_deleted_user(user=user)
        log_audit_event(
            actor=user,
            action="auth.account_deleted",
            target_type="user",
            target_id=str(user.id),
            metadata={"email": archived_record.email, "role": user.role},
        )
        return {"message": "Account deleted successfully."}
