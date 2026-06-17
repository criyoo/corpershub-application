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
        for host in ("10.10.0.13:8000", "localhost:8000"):
            with self.subTest(host=host):
                response = self.client.get("/healthz/", HTTP_HOST=host)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})
