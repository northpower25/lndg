from __future__ import annotations

from datetime import datetime

from asgiref.sync import sync_to_async
from django.utils import timezone

from gui.models import ChannelSnapshot, PeerNetworkSnapshot


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
            # Fee-policy fields default to 0/False until adapters expose policy metadata in list_channels().
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


async def collect_peer_network_snapshots(
    read_adapter, *, snapshot_at: datetime | None = None, batch_size: int = 200
) -> int:
    """Collect gossip-network snapshots for all currently connected peers (6-C).

    Queries the backend adapter for each peer's network-wide channel count,
    total capacity, and average fee rate.  Results are stored in
    ``PeerNetworkSnapshot`` for use by the recommendation engine.
    """
    from gui.models import Channels as DbChannels

    snapshot_time = snapshot_at or timezone.now()

    # Collect distinct peer pubkeys from open/active channels
    pubkeys: list[str] = await sync_to_async(
        lambda: list(
            DbChannels.objects.filter(is_open=True, is_active=True)
            .values_list("remote_pubkey", flat=True)
            .distinct()[:200]
        )
    )()
    if not pubkeys:
        return 0

    peer_infos = read_adapter.get_peer_network_info(pubkeys)
    if not peer_infos:
        return 0

    snapshots = [
        PeerNetworkSnapshot(
            timestamp=snapshot_time,
            pubkey=info.pubkey,
            alias=info.alias,
            channel_count=info.channel_count,
            total_capacity_sat=info.total_capacity_sat,
            avg_fee_rate_ppm=info.avg_fee_rate_ppm,
            last_gossip_update=info.last_gossip_update,
        )
        for info in peer_infos
    ]
    await PeerNetworkSnapshot.objects.abulk_create(snapshots, batch_size=batch_size)
    return len(snapshots)
