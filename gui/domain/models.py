from dataclasses import dataclass
from datetime import datetime
from typing import Literal


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


@dataclass(frozen=True)
class FeePolicy:
    channel_id: str
    fee_rate_ppm: int
    base_fee_msat: int
    inbound_fee_rate_ppm: int
    min_htlc_msat: int
    max_htlc_msat: int


@dataclass(frozen=True)
class SpliceAction:
    channel_id: str
    direction: Literal["in", "out"]
    amount_sat: int
    requested_at: datetime
