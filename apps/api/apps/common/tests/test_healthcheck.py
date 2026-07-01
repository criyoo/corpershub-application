from django.core.exceptions import DisallowedHost
from django.test import SimpleTestCase, override_settings
from django.http import HttpRequest


class HealthCheckTests(SimpleTestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_legacy_health_endpoint_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(ALLOWED_HOSTS=["api.dev.corpershub.ng"])
    def test_health_endpoints_allow_internal_probe_hosts(self):
        for host in ("10.10.0.13:8000", "localhost:8000"):
            with self.subTest(host=host):
                response = self.client.get("/healthz/", HTTP_HOST=host)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(ALLOWED_HOSTS=["api.dev.corpershub.ng"])
    def test_disallowed_host_on_health_path_returns_ok(self):
        """Ensure DisallowedHost for health check paths returns 200, not 400."""
        request = HttpRequest()
        request.path = "/healthz/"
        request.path_info = "/healthz/"
        request.META["HTTP_HOST"] = "10.10.0.13"

        from apps.common.middleware import HealthCheckCommonMiddleware

        def get_response(req):
            # Simulate what Django does - raise DisallowedHost when host is invalid
            req.get_host()
            return None

        middleware = HealthCheckCommonMiddleware(get_response)
        response = middleware.process_exception(request, DisallowedHost("Invalid host"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
