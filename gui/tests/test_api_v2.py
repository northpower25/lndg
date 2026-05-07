from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django.test import TestCase

from gui.models import UserMode


class ApiV2Tests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = APIClient().get("/api/v2/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class UserSettingsApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_user_settings_returns_defaults(self):
        response = self.client.get("/api/v2/user/settings/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], UserMode.MODE_ADVANCED)
        self.assertEqual(data["ai_mode"], UserMode.AI_MODE_OFF)

    def test_put_user_settings_updates_mode(self):
        response = self.client.put(
            "/api/v2/user/settings/",
            {"mode": "expert"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "expert")
        self.assertEqual(UserMode.load().mode, "expert")

    def test_put_user_settings_rejects_invalid_mode(self):
        response = self.client.put(
            "/api/v2/user/settings/",
            {"mode": "invalid_mode"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_access_is_rejected(self):
        anon = APIClient()
        response = anon.get("/api/v2/user/settings/")
        self.assertIn(response.status_code, [401, 403])
