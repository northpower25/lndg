from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from gui.models import ChannelSnapshot


def normalize_snapshot_interval_minutes(
    configured_minutes: int | None, *, default_minutes: int = 15
) -> int:
    if configured_minutes is None:
        return default_minutes
    return configured_minutes if configured_minutes > 0 else default_minutes


async def collect_channel_snapshots(
    read_adapter, *, snapshot_at: datetime | None = None, batch_size: int = 500
) -> int:
    """Collect channel snapshots from the active backend adapter."""
    snapshot_time = snapshot_at or timezone.now()
    channels = read_adapter.list_channels()
    snapshots = [
        ChannelSnapshot(
            timestamp=snapshot_time,
            channel_id=channel.channel_id,
            local_balance_sat=channel.local_balance_sat,
            remote_balance_sat=channel.remote_balance_sat,
            capacity_sat=channel.capacity_sat,
            # Domain Channel currently does not expose local fee-policy flags.
            # They are initialized with safe defaults and will be populated
            # when backend adapters expose fee-policy metadata in list_channels().
            local_fee_rate=0,
            local_base_fee=0,
            local_disabled=False,
            is_active=channel.is_active,
        )
        for channel in channels
    ]
    if not snapshots:
        return 0
    await ChannelSnapshot.objects.abulk_create(snapshots, batch_size=batch_size)
    return len(snapshots)
