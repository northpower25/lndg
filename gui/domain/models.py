from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class AssetContext:
    """Identifies the asset denomination.  Defaults to BTC (sats / msats)."""

    asset_id: str = "btc"
    asset_group: str = "bitcoin"
    denomination: str = "msat"
    display_unit: str = "sats"
    decimals: int = 0


_BTC = AssetContext()


@dataclass(frozen=True)
class Node:
    pubkey: str
    alias: str
    color: str
    version: str
    uris: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Channel:
    channel_id: str
    remote_pubkey: str
    capacity_sat: int
    local_balance_sat: int
    remote_balance_sat: int
    is_active: bool
    is_open: bool


@dataclass(frozen=True)
class Peer:
    pubkey: str
    alias: str | None
    connected: bool
    ping_time_ms: int


@dataclass(frozen=True)
class ForwardingEvent:
    channel_id_in: str
    channel_id_out: str
    amount_in_msat: int
    amount_out_msat: int
    fee_msat: int
    forwarded_at: datetime
    asset: AssetContext = field(default_factory=AssetContext)


@dataclass(frozen=True)
class LiquidityState:
    channel_id: str
    local_balance_msat: int
    remote_balance_msat: int
    capacity_sat: int
    asset: AssetContext = field(default_factory=AssetContext)


@dataclass(frozen=True)
class FeePolicy:
    channel_id: str
    fee_rate_ppm: int
    base_fee_msat: int
    inbound_fee_rate_ppm: int
    min_htlc_msat: int
    max_htlc_msat: int
    asset: AssetContext = field(default_factory=AssetContext)


@dataclass(frozen=True)
class SpliceAction:
    channel_id: str
    direction: Literal["in", "out"]
    amount_sat: int
    requested_at: datetime


@dataclass(frozen=True)
class PeerNetworkInfo:
    """Gossip-network statistics for a single peer pubkey.

    Populated from LND ``GetNodeInfo`` / CLN ``listnodes``.  Used by the
    recommendation engine for dynamic fee-target adjustment (6-C).
    """

    pubkey: str
    alias: str
    channel_count: int
    total_capacity_sat: int
    avg_fee_rate_ppm: float
    last_gossip_update: datetime | None = None


@dataclass(frozen=True)
class RebalanceAction:
    source_channel_id: str
    target_channel_id: str
    amount_sat: int
    max_fee_sat: int
    initiated_at: datetime
    status: Literal["pending", "succeeded", "failed"] = "pending"
    fees_paid_sat: int | None = None
