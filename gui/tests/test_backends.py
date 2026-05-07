"""Tests for the backend interfaces and BackendCapabilities."""

from django.test import SimpleTestCase

from gui.backends import BackendCapabilities


class BackendCapabilitiesTests(SimpleTestCase):
    def test_defaults_are_all_false(self):
        caps = BackendCapabilities()
        self.assertFalse(caps.can_auto_fee)
        self.assertFalse(caps.can_rebalance)
        self.assertFalse(caps.can_splice)
        self.assertFalse(caps.can_inbound_fees)
        self.assertFalse(caps.can_keysend)
        self.assertFalse(caps.supports_plugins)
        self.assertFalse(caps.can_multi_asset)
        self.assertEqual(caps.ai_safe_actions, [])

    def test_lnd_capabilities(self):
        from gui.backends.lnd_backend import LndBackend

        # We cannot instantiate LndBackend in tests (no real gRPC available),
        # but we can call get_capabilities() without connecting.
        backend = LndBackend()
        # Override _get_stub to avoid network calls
        caps = backend.get_capabilities()
        self.assertTrue(caps.can_auto_fee)
        self.assertTrue(caps.can_rebalance)
        self.assertFalse(caps.can_splice)
        self.assertTrue(caps.can_keysend)
        self.assertFalse(caps.supports_plugins)
        self.assertIn("update_fee_policy", caps.ai_safe_actions)

    def test_cln_capabilities(self):
        from gui.backends.cln_backend import ClnBackend

        backend = ClnBackend(base_url="https://127.0.0.1:3010", rune="dummy")
        caps = backend.get_capabilities()
        self.assertTrue(caps.can_splice)
        self.assertTrue(caps.supports_plugins)
        self.assertFalse(caps.can_rebalance)
        self.assertIn("update_fee_policy", caps.ai_safe_actions)
