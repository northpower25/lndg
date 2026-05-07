"""Tests for the abstract domain models (gui/domain/)."""

from datetime import datetime, timezone
from django.test import SimpleTestCase

from gui.domain import (
    AssetContext,
    Channel,
    FeePolicy,
    ForwardingEvent,
    LiquidityState,
    Node,
    Peer,
    RebalanceAction,
    SpliceAction,
)


class DomainModelTests(SimpleTestCase):
    def test_asset_context_defaults_to_btc(self):
        asset = AssetContext()
        self.assertEqual(asset.asset_id, "btc")
        self.assertEqual(asset.denomination, "msat")

    def test_channel_is_frozen(self):
        ch = Channel(
            channel_id="1",
            remote_pubkey="pk",
            capacity_sat=1_000_000,
            local_balance_sat=500_000,
            remote_balance_sat=500_000,
            is_active=True,
            is_open=True,
        )
        with self.assertRaises(Exception):
            ch.channel_id = "2"  # type: ignore[misc]

    def test_node_dataclass(self):
        node = Node(pubkey="pk", alias="test", color="#ffffff", version="0.18.0")
        self.assertEqual(node.pubkey, "pk")
        self.assertEqual(node.uris, [])

    def test_peer_dataclass(self):
        peer = Peer(pubkey="pk", alias="alice", connected=True, ping_time_ms=50)
        self.assertTrue(peer.connected)

    def test_forwarding_event_with_custom_asset(self):
        usd = AssetContext(asset_id="usdt.taproot", asset_group="stablecoin", denomination="usd-cent", display_unit="USD", decimals=2)
        ev = ForwardingEvent(
            channel_id_in="1",
            channel_id_out="2",
            amount_in_msat=1000,
            amount_out_msat=990,
            fee_msat=10,
            forwarded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            asset=usd,
        )
        self.assertEqual(ev.asset.asset_id, "usdt.taproot")

    def test_forwarding_event_defaults_to_btc(self):
        ev = ForwardingEvent(
            channel_id_in="1",
            channel_id_out="2",
            amount_in_msat=1000,
            amount_out_msat=990,
            fee_msat=10,
            forwarded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(ev.asset.asset_id, "btc")

    def test_liquidity_state_dataclass(self):
        ls = LiquidityState(
            channel_id="123",
            local_balance_msat=500_000_000,
            remote_balance_msat=500_000_000,
            capacity_sat=1_000_000,
        )
        self.assertEqual(ls.capacity_sat, 1_000_000)

    def test_fee_policy_dataclass(self):
        fp = FeePolicy(
            channel_id="1",
            fee_rate_ppm=500,
            base_fee_msat=1000,
            inbound_fee_rate_ppm=0,
            min_htlc_msat=1000,
            max_htlc_msat=990_000_000,
        )
        self.assertEqual(fp.fee_rate_ppm, 500)

    def test_splice_action_dataclass(self):
        now = datetime.now(tz=timezone.utc)
        sa = SpliceAction(channel_id="1", direction="in", amount_sat=100_000, requested_at=now)
        self.assertEqual(sa.direction, "in")

    def test_rebalance_action_default_status(self):
        now = datetime.now(tz=timezone.utc)
        ra = RebalanceAction(
            source_channel_id="1",
            target_channel_id="2",
            amount_sat=50_000,
            max_fee_sat=100,
            initiated_at=now,
        )
        self.assertEqual(ra.status, "pending")
        self.assertIsNone(ra.fees_paid_sat)
