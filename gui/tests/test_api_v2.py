from rest_framework.test import APIClient

from django.test import TestCase


class ApiV2Tests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = APIClient().get("/api/v2/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
