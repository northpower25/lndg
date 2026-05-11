"""LND gRPC adapter – implements LightningReadAdapter and LightningWriteAdapter.

gRPC credentials are loaded once at module level and the channel is reused for
the entire job lifecycle.  No reconnect per request (R-JOB-2).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import grpc

from gui.domain import (
    Channel,
    FeePolicy,
    ForwardingEvent,
    LiquidityState,
    Node,
    Peer,
    PeerNetworkInfo,
    SpliceAction,
)
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect

from .interfaces import BackendCapabilities, LightningReadAdapter, LightningWriteAdapter

logger = logging.getLogger(__name__)


class LndBackend(LightningReadAdapter, LightningWriteAdapter):
    """LND backend adapter.

    Wraps the existing LND gRPC connection.  The gRPC channel is opened on
    first use and reused for subsequent calls (cached per instance).
    """

    def __init__(self) -> None:
        self._channel: grpc.Channel | None = None
        self._stub: lnrpc.LightningStub | None = None

    # ── Connection helpers ────────────────────────────────────────────────────

    def _get_stub(self) -> lnrpc.LightningStub:
        if self._stub is None:
            self._channel = lnd_connect()
            self._stub = lnrpc.LightningStub(self._channel)
        return self._stub

    # ── LightningReadAdapter ──────────────────────────────────────────────────

    def get_node_info(self) -> Node:
        stub = self._get_stub()
        info = stub.GetInfo(ln.GetInfoRequest())
        return Node(
            pubkey=info.identity_pubkey,
            alias=info.alias,
            color=info.color,
            version=info.version,
            uris=list(info.uris),
        )

    def list_channels(self) -> list[Channel]:
        stub = self._get_stub()
        response = stub.ListChannels(ln.ListChannelsRequest())
        return [
            Channel(
                channel_id=str(ch.chan_id),
                remote_pubkey=ch.remote_pubkey,
                capacity_sat=ch.capacity,
                local_balance_sat=ch.local_balance,
                remote_balance_sat=ch.remote_balance,
                is_active=ch.active,
                is_open=True,
            )
            for ch in response.channels
        ]

    def list_peers(self) -> list[Peer]:
        stub = self._get_stub()
        response = stub.ListPeers(ln.ListPeersRequest())
        return [
            Peer(
                pubkey=p.pub_key,
                alias=None,
                connected=True,
                ping_time_ms=p.ping_time,
            )
            for p in response.peers
        ]

    def get_forwarding_events(
        self, start: datetime, end: datetime
    ) -> list[ForwardingEvent]:
        stub = self._get_stub()
        start_ts = int(start.replace(tzinfo=timezone.utc).timestamp())
        end_ts = int(end.replace(tzinfo=timezone.utc).timestamp())
        response = stub.ForwardingHistory(
            ln.ForwardingHistoryRequest(start_time=start_ts, end_time=end_ts)
        )
        return [
            ForwardingEvent(
                channel_id_in=str(ev.chan_id_in),
                channel_id_out=str(ev.chan_id_out),
                amount_in_msat=ev.amt_in_msat,
                amount_out_msat=ev.amt_out_msat,
                fee_msat=ev.fee_msat,
                forwarded_at=datetime.fromtimestamp(
                    ev.timestamp, tz=timezone.utc
                ),
            )
            for ev in response.forwarding_events
        ]

    def get_liquidity_state(self, channel_id: str) -> LiquidityState:
        channels = self.list_channels()
        for ch in channels:
            if ch.channel_id == channel_id:
                return LiquidityState(
                    channel_id=channel_id,
                    local_balance_msat=ch.local_balance_sat * 1000,
                    remote_balance_msat=ch.remote_balance_sat * 1000,
                    capacity_sat=ch.capacity_sat,
                )
        raise ValueError(f"Channel {channel_id!r} not found")

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            can_auto_fee=True,
            can_rebalance=True,
            can_stream_htlcs=True,
            can_splice=False,
            can_inbound_fees=True,
            can_keysend=True,
            supports_plugins=False,
            can_multi_asset=False,
            ai_safe_actions=["update_fee_policy"],
        )

    def get_peer_network_info(self, pubkeys: list[str]) -> list[PeerNetworkInfo]:
        """Fetch gossip-network statistics for each pubkey via LND GetNodeInfo."""
        stub = self._get_stub()
        results: list[PeerNetworkInfo] = []
        for pubkey in pubkeys:
            try:
                resp = stub.GetNodeInfo(
                    ln.NodeInfoRequest(pub_key=pubkey, include_channels=True)
                )
                node = resp.node
                channels = resp.channels
                avg_fee_rate = 0.0
                if channels:
                    fee_rates = []
                    for ch in channels:
                        p1 = ch.node1_policy
                        p2 = ch.node2_policy
                        if p1 and p1.fee_rate_milli_msat:
                            fee_rates.append(p1.fee_rate_milli_msat)
                        if p2 and p2.fee_rate_milli_msat:
                            fee_rates.append(p2.fee_rate_milli_msat)
                    if fee_rates:
                        avg_fee_rate = sum(fee_rates) / len(fee_rates)
                last_update = None
                if node.last_update:
                    last_update = datetime.fromtimestamp(node.last_update, tz=timezone.utc)
                results.append(
                    PeerNetworkInfo(
                        pubkey=pubkey,
                        alias=node.alias or "",
                        channel_count=resp.num_channels,
                        total_capacity_sat=resp.total_capacity,
                        avg_fee_rate_ppm=avg_fee_rate,
                        last_gossip_update=last_update,
                    )
                )
            except Exception as exc:
                logger.debug("GetNodeInfo failed for %s: %s", pubkey[:16], exc)
        return results

    # ── LightningWriteAdapter ─────────────────────────────────────────────────

    def update_fee_policy(self, channel_id: str, policy: FeePolicy) -> bool:
        """Apply fee policy to the given channel via LND gRPC.

        The channel_id must be resolvable to a channel point (funding_txid:output_index)
        from the local database.
        """
        from gui.models import Channels as DbChannels

        try:
            db_channel = DbChannels.objects.get(chan_id=channel_id)
        except DbChannels.DoesNotExist:
            logger.error("update_fee_policy: channel %s not found in DB", channel_id)
            return False

        channel_point = ln.ChannelPoint(
            funding_txid_str=db_channel.funding_txid,
            output_index=db_channel.output_index,
        )
        stub = self._get_stub()
        try:
            stub.UpdateChannelPolicy(
                ln.PolicyUpdateRequest(
                    chan_point=channel_point,
                    base_fee_msat=policy.base_fee_msat,
                    fee_rate=policy.fee_rate_ppm / 1_000_000.0,
                    time_lock_delta=db_channel.local_cltv,
                    min_htlc_msat_specified=True,
                    min_htlc_msat=policy.min_htlc_msat,
                    max_htlc_msat=policy.max_htlc_msat,
                )
            )
            return True
        except grpc.RpcError as exc:
            logger.error("update_fee_policy gRPC error: %s", exc)
            return False

    def splice_in(
        self, channel_id: str, amount_sat: int, fee_rate: int
    ) -> SpliceAction:
        raise NotImplementedError("LND does not support channel splicing yet.")

    def splice_out(
        self,
        channel_id: str,
        amount_sat: int,
        destination: str,
        fee_rate: int,
    ) -> SpliceAction:
        raise NotImplementedError("LND does not support channel splicing yet.")

    def get_splice_status(self, splice_id: str) -> SpliceAction:
        raise NotImplementedError("LND does not support channel splicing yet.")
