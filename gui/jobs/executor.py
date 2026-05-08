from __future__ import annotations

from gui.backends.interfaces import LightningWriteAdapter
from gui.backends.registry import get_active_backend
from gui.domain import SpliceAction


def _get_write_backend() -> LightningWriteAdapter:
    backend = get_active_backend()
    if backend is None:
        raise RuntimeError("No active backend configured.")
    return backend


def execute_splice_in(channel_id: str, amount_sat: int, fee_rate: int) -> SpliceAction:
    backend = _get_write_backend()
    return backend.splice_in(channel_id=channel_id, amount_sat=amount_sat, fee_rate=fee_rate)


def execute_splice_out(
    channel_id: str, amount_sat: int, destination: str, fee_rate: int
) -> SpliceAction:
    backend = _get_write_backend()
    return backend.splice_out(
        channel_id=channel_id,
        amount_sat=amount_sat,
        destination=destination,
        fee_rate=fee_rate,
    )


def execute_splice_status(splice_id: str) -> SpliceAction:
    backend = _get_write_backend()
    return backend.get_splice_status(splice_id=splice_id)
