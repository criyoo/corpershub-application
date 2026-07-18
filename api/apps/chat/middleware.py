from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.security.websocket import AllowedHostsOriginValidator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_for_token(token: str):
    user_model = get_user_model()
    try:
        validated = AccessToken(token)
        return user_model.objects.get(id=validated["user_id"])
    except Exception:
        from django.contrib.auth.models import AnonymousUser

        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        query_params = parse_qs(scope["query_string"].decode())
        token = query_params.get("token", [None])[0]
        scope["user"] = await get_user_for_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return AllowedHostsOriginValidator(JWTAuthMiddleware(AuthMiddlewareStack(inner)))
