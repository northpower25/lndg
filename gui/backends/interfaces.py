"""Abstract Lightning backend interfaces.

The read/write separation is a structural security constraint: AI/ML modules and
the recommendation engine may only import and use ``LightningReadAdapter``.
``LightningWriteAdapter`` must only be imported by ``executor.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from gui.domain import (
    Channel,
    FeePolicy,
    ForwardingEvent,
    LiquidityState,
    Node,
    Peer,
    SpliceAction,
)

from datetime import datetime


@dataclass
class BackendCapabilities:
    """Capability flags reported by each backend implementation."""

    can_auto_fee: bool = False
    """Fee adjustment via API is possible."""

    can_rebalance: bool = False
    """Circular payments for rebalancing are supported."""

    can_stream_htlcs: bool = False
    """Live HTLC-event stream is available."""

    can_splice: bool = False
    """Channel splice (resize without close) is supported."""

    can_inbound_fees: bool = False
    """Inbound-fee parameters are supported."""

    can_keysend: bool = False
    """Spontaneous payments (keysend) are supported."""

    supports_plugins: bool = False
    """Plugin extension mechanism is present (CLN)."""

    can_multi_asset: bool = False
    """Multi-asset channels (Taproot Assets) – reserved for Phase 7."""

    ai_safe_actions: list[str] = field(default_factory=list)
    """Which WriteAdapter actions are approved for policy-bound automation.

    Example: ``['update_fee_policy']``.  Never ``splice_in``/``splice_out``
    without explicit expert opt-in.
    """


class LightningReadAdapter(ABC):
    """Read-only Lightning backend interface.

    May be imported and used by views, recommendation engine, and AI/ML modules.
    """

    @abstractmethod
    def get_node_info(self) -> Node:
        """Return basic information about the local node."""

    @abstractmethod
    def list_channels(self) -> list[Channel]:
        """Return all channels (open and recently closed)."""

    @abstractmethod
    def list_peers(self) -> list[Peer]:
        """Return all connected and known peers."""

    @abstractmethod
    def get_forwarding_events(
        self, start: datetime, end: datetime
    ) -> list[ForwardingEvent]:
        """Return forwarding events in the given time range."""

    @abstractmethod
    def get_liquidity_state(self, channel_id: str) -> LiquidityState:
        """Return a liquidity snapshot for a single channel."""

    @abstractmethod
    def get_capabilities(self) -> BackendCapabilities:
        """Return the capabilities supported by this backend."""


class LightningWriteAdapter(ABC):
    """Write-access Lightning backend interface.

    **Must only be imported by** ``executor.py``.
    Never import from views, templates, recommendation engine, or AI/ML modules.
    """

    @abstractmethod
    def update_fee_policy(self, channel_id: str, policy: FeePolicy) -> bool:
        """Apply the given fee policy to the channel.  Returns True on success."""

    @abstractmethod
    def splice_in(
        self, channel_id: str, amount_sat: int, fee_rate: int
    ) -> SpliceAction:
        """Add liquidity to an existing channel without closing it."""

    @abstractmethod
    def splice_out(
        self,
        channel_id: str,
        amount_sat: int,
        destination: str,
        fee_rate: int,
    ) -> SpliceAction:
        """Remove liquidity from an existing channel without closing it."""

    @abstractmethod
    def get_splice_status(self, splice_id: str) -> SpliceAction:
        """Return the current status of a splice operation."""
