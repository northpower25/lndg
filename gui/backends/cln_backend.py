"""CLN (Core Lightning) backend – connects via clnrest HTTP REST API.

Phase 1 implements basic read methods; Phase 2 adds ``get_forwarding_events``,
``update_fee_policy``, and runtime plugin detection in ``get_capabilities``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

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
    ``get_capabilities``.

    Phase 2 adds: ``get_forwarding_events``, ``update_fee_policy``, runtime
    plugin detection (``rebalance``, htlc-stream).
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
        # Pass a CA certificate path to enable TLS verification,
        # or None to use the default system CA bundle.
        # Setting verify=False disables TLS verification (not recommended for production).
        self._ca_cert: str | bool = ca_cert if ca_cert is not None else True
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
        """Return forwarding events in the given time range via CLN ``listforwards``."""
        params: dict = {"status": "settled"}
        data = self._post("listforwards", params)
        events: list[ForwardingEvent] = []
        start_ts = start.timestamp()
        end_ts = end.timestamp()
        for fwd in data.get("forwards", []):
            received_ts = fwd.get("received_time", 0)
            if not (start_ts <= received_ts < end_ts):
                continue
            events.append(
                ForwardingEvent(
                    channel_id_in=str(fwd.get("in_channel", "")),
                    channel_id_out=str(fwd.get("out_channel", "")),
                    amount_in_msat=fwd.get("in_msat", 0),
                    amount_out_msat=fwd.get("out_msat", 0),
                    fee_msat=fwd.get("fee_msat", 0),
                    forwarded_at=datetime.fromtimestamp(received_ts, tz=dt_timezone.utc),
                )
            )
        return events

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

        Plugin availability is detected at runtime by querying ``listplugins``.
        ``can_splice`` is True for CLN >= v24.02.
        ``supports_plugins`` is always True for CLN.
        """
        can_rebalance = False
        can_stream_htlcs = False
        try:
            plugins_data = self._post("listplugins")
            active_plugin_names = {
                p.get("name", "")
                for p in plugins_data.get("plugins", [])
                if p.get("active", False)
            }
            can_rebalance = any(
                "rebalance" in name for name in active_plugin_names
            )
            can_stream_htlcs = any(
                "htlcstream" in name or "htlc_stream" in name or "htlc-stream" in name
                for name in active_plugin_names
            )
        except Exception:
            logger.debug("CLN listplugins failed; defaulting to no plugin capabilities")

        return BackendCapabilities(
            can_auto_fee=True,
            can_rebalance=can_rebalance,
            can_stream_htlcs=can_stream_htlcs,
            can_splice=True,       # CLN supports splicing from v24.02
            can_inbound_fees=False,
            can_keysend=True,
            supports_plugins=True,
            can_multi_asset=False,
            ai_safe_actions=["update_fee_policy"],
        )

    # ── LightningWriteAdapter ─────────────────────────────────────────────────

    def update_fee_policy(self, channel_id: str, policy: FeePolicy) -> bool:
        """Apply fee policy to the given channel via CLN ``setchannel``."""
        params: dict = {
            "id": channel_id,
            "feebase": policy.base_fee_msat,
            "feeppm": policy.fee_rate_ppm,
        }
        if policy.min_htlc_msat > 0:
            params["htlcmin"] = f"{policy.min_htlc_msat}msat"
        if policy.max_htlc_msat > 0:
            params["htlcmax"] = f"{policy.max_htlc_msat}msat"
        try:
            self._post("setchannel", params)
            return True
        except Exception as exc:
            logger.error("CLN setchannel for %s failed: %s", channel_id, exc)
            return False

    def splice_in(
        self, channel_id: str, amount_sat: int, fee_rate: int
    ) -> SpliceAction:
        params = {
            "channel_id": channel_id,
            "amount": f"{amount_sat}sat",
            "feerate_perkw": fee_rate,
        }
        try:
            self._post("splice_init", params)
            return SpliceAction(
                channel_id=channel_id,
                direction="in",
                amount_sat=amount_sat,
                requested_at=datetime.now(tz=dt_timezone.utc),
            )
        except Exception as exc:
            logger.error("CLN splice_in for %s failed: %s", channel_id, exc)
            raise RuntimeError(f"CLN splice_in failed: {exc}") from exc

    def splice_out(
        self,
        channel_id: str,
        amount_sat: int,
        destination: str,
        fee_rate: int,
    ) -> SpliceAction:
        params = {
            "channel_id": channel_id,
            "amount": f"-{amount_sat}sat",
            "destination": destination,
            "feerate_perkw": fee_rate,
        }
        try:
            self._post("splice_init", params)
            return SpliceAction(
                channel_id=channel_id,
                direction="out",
                amount_sat=amount_sat,
                requested_at=datetime.now(tz=dt_timezone.utc),
            )
        except Exception as exc:
            logger.error("CLN splice_out for %s failed: %s", channel_id, exc)
            raise RuntimeError(f"CLN splice_out failed: {exc}") from exc

    def get_splice_status(self, splice_id: str) -> SpliceAction:
        try:
            data = self._post("splice_status", {"id": splice_id})
            status = data.get("status", "")
            direction = "out" if data.get("direction") == "out" else "in"
            amount_sat = int(data.get("amount_sat", 0))
            if status == "out":
                direction = "out"
            return SpliceAction(
                channel_id=str(data.get("channel_id", "")),
                direction=direction,
                amount_sat=amount_sat,
                requested_at=datetime.now(tz=dt_timezone.utc),
            )
        except Exception as exc:
            logger.error("CLN splice_status for %s failed: %s", splice_id, exc)
            raise RuntimeError(f"CLN splice_status failed: {exc}") from exc
