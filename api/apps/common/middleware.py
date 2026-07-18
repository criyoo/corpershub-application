from django.http import JsonResponse


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
