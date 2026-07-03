import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

django_asgi_app = get_asgi_application()

from apps.chat.middleware import JWTAuthMiddlewareStack  # noqa: E402
from apps.chat.routing import websocket_urlpatterns  # noqa: E402


async def health_check_asgi_wrapper(scope, receive, send):
    """Intercept health check requests before Django processes them.

    Industry-standard practice for ALB health checks behind Django:

    ALB health checks send GET requests to /healthz/ with the ALB's private IP
    as the Host header. This bypasses ALLOWED_HOSTS validation entirely by
    responding at the ASGI transport layer, before Django's request pipeline
    (including host validation) runs.

    This also ensures health checks succeed even when:
    - The database is unreachable
    - Redis/Valkey is down
    - Migrations are pending
    - Django is still bootstrapping
    """
    if scope["type"] == "http" and scope.get("path", "").rstrip("/") in ("/healthz", "/health"):
        body = b'{"status":"ok"}'
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
        return
    await django_asgi_app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": health_check_asgi_wrapper,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
