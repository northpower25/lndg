"""CLN (Core Lightning) backend skeleton – connects via clnrest HTTP REST API.

Only basic read methods are implemented in Phase 1 (skeleton).
Full implementation follows in Phase 2.
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from gui.domain import (
    Channel,
    FeePolicy,
    ForwardingEvent,
    LiquidityState,
    Node,
    Peer,
    SpliceAction,
)

from .interfaces import BackendCapabilities, LightningReadAdapter, LightningWriteAdapter

logger = logging.getLogger(__name__)


class ClnBackend(LightningReadAdapter, LightningWriteAdapter):
    """Core Lightning backend adapter (clnrest / HTTP REST).

    Authenticates via a CLN Rune token.  Uses the clnrest plugin available
    from CLN v23.08+ (default enabled from v24.05).

    Phase 1 implements: ``get_node_info``, ``list_channels``, ``list_peers``,
    ``get_capabilities``.  All other methods raise ``NotImplementedError`` and
    will be filled in Phase 2.
    """

    def __init__(
        self,
        base_url: str,
        rune: str,
        *,
        ca_cert: str | None = None,
        timeout: int = 30,
    ) -> None:
        """
        Args:
            base_url: Base URL of the clnrest endpoint, e.g.
                      ``https://127.0.0.1:3010``.
            rune:     CLN Rune token for authentication.
            ca_cert:  Path to the CA certificate file used to verify TLS, or
                      ``None`` to skip verification (not recommended for production).
            timeout:  HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._rune = rune
        self._ca_cert: str | bool = ca_cert if ca_cert is not None else False
        self._timeout = timeout
        self._session: requests.Session | None = None

    # ── Connection helpers ─────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        if self._session is None:
            session = requests.Session()
            session.headers.update({"Rune": self._rune, "Content-Type": "application/json"})
            session.verify = self._ca_cert
            self._session = session
        return self._session

    def _post(self, method: str, params: dict | None = None) -> dict:
        """Call a clnrest method and return the parsed JSON response."""
        session = self._get_session()
        url = f"{self._base_url}/v1/{method}"
        try:
            response = session.post(url, json=params or {}, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("CLN REST call to %s failed: %s", method, exc)
            raise

    # ── LightningReadAdapter ──────────────────────────────────────────────────

    def get_node_info(self) -> Node:
        data = self._post("getinfo")
        return Node(
            pubkey=data.get("id", ""),
            alias=data.get("alias", ""),
            color=data.get("color", ""),
            version=data.get("version", ""),
            uris=[f"{data['id']}@{a}" for a in data.get("address", [])],
        )

    def list_channels(self) -> list[Channel]:
        data = self._post("listpeerchannels")
        channels: list[Channel] = []
        for ch in data.get("channels", []):
            chan_id = str(ch.get("short_channel_id") or ch.get("channel_id", ""))
            channels.append(
                Channel(
                    channel_id=chan_id,
                    remote_pubkey=ch.get("peer_id", ""),
                    capacity_sat=ch.get("total_msat", 0) // 1000,
                    local_balance_sat=ch.get("to_us_msat", 0) // 1000,
                    remote_balance_sat=(
                        ch.get("total_msat", 0) - ch.get("to_us_msat", 0)
                    ) // 1000,
                    is_active=ch.get("peer_connected", False),
                    is_open=ch.get("state", "") == "CHANNELD_NORMAL",
                )
            )
        return channels

    def list_peers(self) -> list[Peer]:
        data = self._post("listpeers")
        peers: list[Peer] = []
        for p in data.get("peers", []):
            peers.append(
                Peer(
                    pubkey=p.get("id", ""),
                    alias=None,
                    connected=p.get("connected", False),
                    ping_time_ms=0,
                )
            )
        return peers

    def get_forwarding_events(
        self, start: datetime, end: datetime
    ) -> list[ForwardingEvent]:
        # Phase 2: use listforwards with start/end filtering
        raise NotImplementedError("CLN forwarding events will be implemented in Phase 2.")

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
        """Return CLN-specific capability flags.

        ``can_splice`` is True for CLN >= v24.02.
        ``supports_plugins`` is always True for CLN.
        """
        return BackendCapabilities(
            can_auto_fee=True,
            can_rebalance=False,   # requires the 'rebalance' plugin – detected at runtime in Phase 2
            can_stream_htlcs=False,
            can_splice=True,       # CLN supports splicing from v24.02
            can_inbound_fees=False,
            can_keysend=True,
            supports_plugins=True,
            can_multi_asset=False,
            ai_safe_actions=["update_fee_policy"],
        )

    # ── LightningWriteAdapter ─────────────────────────────────────────────────

    def update_fee_policy(self, channel_id: str, policy: FeePolicy) -> bool:
        # Phase 2: implement via setchannel
        raise NotImplementedError("CLN fee update will be implemented in Phase 2.")

    def splice_in(
        self, channel_id: str, amount_sat: int, fee_rate: int
    ) -> SpliceAction:
        # Phase 3: guided splice workflow
        raise NotImplementedError("CLN splice_in will be implemented in Phase 3.")

    def splice_out(
        self,
        channel_id: str,
        amount_sat: int,
        destination: str,
        fee_rate: int,
    ) -> SpliceAction:
        raise NotImplementedError("CLN splice_out will be implemented in Phase 3.")

    def get_splice_status(self, splice_id: str) -> SpliceAction:
        raise NotImplementedError("CLN splice status will be implemented in Phase 3.")
