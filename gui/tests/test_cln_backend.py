"""Integration tests for ClnBackend using a mock HTTP server."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from gui.backends.cln_backend import ClnBackend
from gui.domain import FeePolicy


def _make_mock_response(payload: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class ClnGetForwardingEventsTests(SimpleTestCase):
    """Tests for ClnBackend.get_forwarding_events."""

    def _backend(self):
        return ClnBackend(base_url="https://127.0.0.1:3010", rune="testrune")

    def test_returns_events_within_range(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        start_ts = start.timestamp()
        end_ts = end.timestamp()
        mid_ts = (start_ts + end_ts) / 2

        payload = {
            "forwards": [
                {
                    "in_channel": "111x1x1",
                    "out_channel": "222x2x2",
                    "in_msat": 1_200_000,
                    "out_msat": 1_000_000,
                    "fee_msat": 200,
                    "status": "settled",
                    "received_time": mid_ts,
                },
                {
                    "in_channel": "333x3x3",
                    "out_channel": "444x4x4",
                    "in_msat": 500_000,
                    "out_msat": 490_000,
                    "fee_msat": 10,
                    "status": "settled",
                    # outside range – before start
                    "received_time": start_ts - 1,
                },
            ]
        }
        backend = self._backend()
        with patch.object(backend, "_post", return_value=payload):
            events = backend.get_forwarding_events(start, end)

        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.channel_id_in, "111x1x1")
        self.assertEqual(ev.channel_id_out, "222x2x2")
        self.assertEqual(ev.amount_in_msat, 1_200_000)
        self.assertEqual(ev.fee_msat, 200)

    def test_empty_when_no_forwards(self):
        backend = self._backend()
        with patch.object(backend, "_post", return_value={"forwards": []}):
            events = backend.get_forwarding_events(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 2, tzinfo=timezone.utc),
            )
        self.assertEqual(events, [])


class ClnUpdateFeePolicyTests(SimpleTestCase):
    """Tests for ClnBackend.update_fee_policy."""

    def _backend(self):
        return ClnBackend(base_url="https://127.0.0.1:3010", rune="testrune")

    def test_success_returns_true(self):
        policy = FeePolicy(
            channel_id="123x4x5",
            fee_rate_ppm=500,
            base_fee_msat=1000,
            inbound_fee_rate_ppm=0,
            min_htlc_msat=1000,
            max_htlc_msat=1_000_000_000,
        )
        backend = self._backend()
        with patch.object(backend, "_post", return_value={"channels": []}) as mock_post:
            result = backend.update_fee_policy("123x4x5", policy)

        self.assertTrue(result)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "setchannel")
        params = call_args[0][1]
        self.assertEqual(params["id"], "123x4x5")
        self.assertEqual(params["feebase"], 1000)
        self.assertEqual(params["feeppm"], 500)

    def test_failure_returns_false(self):
        import requests

        policy = FeePolicy(
            channel_id="err",
            fee_rate_ppm=100,
            base_fee_msat=0,
            inbound_fee_rate_ppm=0,
            min_htlc_msat=0,
            max_htlc_msat=0,
        )
        backend = self._backend()
        with patch.object(backend, "_post", side_effect=requests.RequestException("timeout")):
            result = backend.update_fee_policy("err", policy)
        self.assertFalse(result)


class ClnGetCapabilitiesTests(SimpleTestCase):
    """Tests for ClnBackend.get_capabilities with plugin detection."""

    def _backend(self):
        return ClnBackend(base_url="https://127.0.0.1:3010", rune="testrune")

    def test_rebalance_plugin_active_sets_can_rebalance(self):
        plugins_payload = {
            "plugins": [
                {"name": "/usr/lib/cln/plugins/rebalance", "active": True},
            ]
        }
        backend = self._backend()
        with patch.object(backend, "_post", return_value=plugins_payload):
            caps = backend.get_capabilities()
        self.assertTrue(caps.can_rebalance)
        self.assertTrue(caps.supports_plugins)

    def test_no_rebalance_plugin_sets_can_rebalance_false(self):
        plugins_payload = {
            "plugins": [
                {"name": "/usr/lib/cln/plugins/pay", "active": True},
            ]
        }
        backend = self._backend()
        with patch.object(backend, "_post", return_value=plugins_payload):
            caps = backend.get_capabilities()
        self.assertFalse(caps.can_rebalance)

    def test_listplugins_failure_falls_back_to_defaults(self):
        import requests

        backend = self._backend()
        with patch.object(backend, "_post", side_effect=requests.RequestException("conn refused")):
            caps = backend.get_capabilities()
        # Should not raise; falls back gracefully
        self.assertFalse(caps.can_rebalance)
        self.assertTrue(caps.supports_plugins)
        self.assertTrue(caps.can_splice)
