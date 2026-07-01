from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.accounts.account_lifecycle import deactivate_expired_corper_account
from apps.accounts.presence import touch_user_presence


class CorpersJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as exc:
            raise InvalidToken(_("Token contained no recognizable user identification")) from exc

        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except user_model.DoesNotExist as exc:
            raise AuthenticationFailed(_("User not found"), code="user_not_found") from exc

        deactivate_expired_corper_account(user=user)
        if not user.is_active:
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        if api_settings.CHECK_REVOKE_TOKEN:
            if validated_token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
                raise AuthenticationFailed(_("The user's password has been changed."), code="password_changed")

        touch_user_presence(user=user)
        return user
