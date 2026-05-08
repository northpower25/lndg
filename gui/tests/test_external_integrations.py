from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from gui.jobs.external_integrations import classify_fee_signal, get_amboss_peer_context, get_mempool_recommended_fees


class ExternalIntegrationsTests(SimpleTestCase):
    def test_classify_fee_signal_low_medium_high(self):
        self.assertEqual(classify_fee_signal({"hourFee": 8}).light, "🟢")
        self.assertEqual(classify_fee_signal({"hourFee": 20}).light, "🟡")
        self.assertEqual(classify_fee_signal({"hourFee": 80}).light, "🔴")

    def test_mempool_fetch_is_disabled_without_opt_in(self):
        self.assertIsNone(get_mempool_recommended_fees(enabled=False))

    @patch("gui.jobs.external_integrations.requests.post")
    def test_amboss_context_fetches_only_requested_pubkeys(self, mock_post):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "getNodes": [
                    {"publicKey": "abc", "rank": 5, "capacity": 1000, "channels": 2},
                    {"publicKey": "def", "rank": 7, "capacity": 500, "channels": 1},
                ]
            }
        }
        mock_post.return_value = response

        result = get_amboss_peer_context(
            enabled=True,
            api_key="test-key",
            pubkeys=["abc", "def"],
        )
        self.assertIn("abc", result)
        self.assertEqual(result["abc"]["rank"], 5)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sorted(payload["variables"]["pubkeys"]), ["abc", "def"])
