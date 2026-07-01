from django.test import SimpleTestCase, override_settings


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
        """Health endpoints should return OK even with invalid Host headers.

        When USE_X_FORWARDED_HOST is True (production setting), ALB health checks
        send internal task IPs as the Host header. The HealthCheckCommonMiddleware
        catches DisallowedHost exceptions for health check paths and returns OK.
        """
        for host in ("10.10.0.13:8000", "localhost:8000"):
            with self.subTest(host=host):
                response = self.client.get("/healthz/", HTTP_HOST=host)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})
