from django.http import JsonResponse


class HealthCheckCommonMiddleware:
    """Handle health check requests before Django's host validation.

    When USE_X_FORWARDED_HOST is True, ALB health checks send internal IPs as the Host header.
    For health check endpoints, we catch DisallowedHost exceptions and return a valid response.
    """

    HEALTH_PATH_PREFIXES = ("/health", "/healthz")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Handle DisallowedHost exceptions for health check endpoints
        if request.path.split("/")[1] in ("health", "healthz"):
            from django.core.exceptions import DisallowedHost

            if isinstance(exception, DisallowedHost):
                return JsonResponse({"status": "ok"})
        return None