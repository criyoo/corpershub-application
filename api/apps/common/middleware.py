from asgiref.sync import iscoroutinefunction, sync_to_async
from django.http import JsonResponse
from django.utils.decorators import sync_and_async_middleware


def prepare_asgi_streaming_response(request, response):
    if (
        not hasattr(request, "scope")
        or not getattr(response, "streaming", False)
        or getattr(response, "is_async", False)
    ):
        return response

    streaming_content = response.streaming_content

    async def async_streaming_content():
        for part in await sync_to_async(list)(streaming_content):
            yield part

    response.streaming_content = async_streaming_content()
    return response


@sync_and_async_middleware
def AsyncStreamingResponseMiddleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            response = await get_response(request)
            return prepare_asgi_streaming_response(request, response)

        return middleware

    def middleware(request):
        response = get_response(request)
        return prepare_asgi_streaming_response(request, response)

    return middleware


class HealthCheckCommonMiddleware:
    """Handle health check requests before Django's host validation.

    ALB health checks send private IP addresses as the Host header, which fails
    ALLOWED_HOSTS validation. This middleware intercepts those requests before host
    validation occurs and returns a valid 200 response.
    """

    HEALTH_PATH_PREFIXES = ("/health", "/healthz")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Fast-path: skip host validation for health check endpoints entirely.
        # ALB health checks send the private IP as Host header, which triggers
        # DisallowedHost → 400. We intercept before that happens.
        path = request.path
        if path.startswith(self.HEALTH_PATH_PREFIXES):
            return JsonResponse({"status": "ok"})

        return self.get_response(request)
