from django.middleware.common import CommonMiddleware


class HealthCheckCommonMiddleware(CommonMiddleware):
    """Skip host validation for internal health probes that hit task IPs directly."""

    HEALTH_PATH_PREFIXES = ("/health", "/healthz")

    def process_request(self, request):
        if request.path_info.rstrip("/") in self.HEALTH_PATH_PREFIXES:
            return None
        return super().process_request(request)
