"""Tests for the capability registry and the /api/v2/capabilities/ endpoint."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from gui.backends.interfaces import BackendCapabilities
from gui.backends.registry import get_capabilities, set_active_backend


class CapabilityRegistryTests(SimpleTestCase):
    def test_returns_defaults_when_no_backend_set(self):
        # Reset registry
        import gui.backends.registry as reg

        orig = reg._active_backend
        reg._active_backend = None
        try:
            caps = get_capabilities()
            self.assertIsInstance(caps, BackendCapabilities)
            self.assertFalse(caps.can_auto_fee)
        finally:
            reg._active_backend = orig

    def test_returns_backend_capabilities_after_set(self):
        class _FakeBackend:
            def get_capabilities(self):
                return BackendCapabilities(can_auto_fee=True, can_splice=True)

        import gui.backends.registry as reg

        orig = reg._active_backend
        try:
            set_active_backend(_FakeBackend())
            caps = get_capabilities()
            self.assertTrue(caps.can_auto_fee)
            self.assertTrue(caps.can_splice)
        finally:
            reg._active_backend = orig

    def test_falls_back_on_exception(self):
        class _BrokenBackend:
            def get_capabilities(self):
                raise RuntimeError("backend unavailable")

        import gui.backends.registry as reg

        orig = reg._active_backend
        try:
            set_active_backend(_BrokenBackend())
            caps = get_capabilities()
            self.assertIsInstance(caps, BackendCapabilities)
            self.assertFalse(caps.can_auto_fee)
        finally:
            reg._active_backend = orig


class CapabilitiesApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="captest", password="cappass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_capabilities_endpoint_returns_200(self):
        response = self.client.get("/api/v2/capabilities/")
        self.assertEqual(response.status_code, 200)

    def test_capabilities_endpoint_returns_expected_fields(self):
        response = self.client.get("/api/v2/capabilities/")
        data = response.json()
        expected_fields = {
            "can_auto_fee",
            "can_rebalance",
            "can_stream_htlcs",
            "can_splice",
            "can_inbound_fees",
            "can_keysend",
            "supports_plugins",
            "can_multi_asset",
            "ai_safe_actions",
        }
        self.assertTrue(expected_fields.issubset(data.keys()))

    def test_capabilities_endpoint_requires_authentication(self):
        anon = APIClient()
        response = anon.get("/api/v2/capabilities/")
        self.assertIn(response.status_code, [401, 403])
