from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from gui.models import FailedHTLCs, ForwardingAggregate, Forwards

WINDOW_TO_DELTA = {
    ForwardingAggregate.WINDOW_1D: timedelta(days=1),
    ForwardingAggregate.WINDOW_7D: timedelta(days=7),
    ForwardingAggregate.WINDOW_30D: timedelta(days=30),
}


def _fee_sat_to_msat(fee_sat: float | int | Decimal) -> int:
    fee_sat = Decimal(str(fee_sat))
    return int((fee_sat * Decimal("1000")).to_integral_value(rounding=ROUND_HALF_UP))


async def aggregate_forwarding_windows(
    windows: tuple[str, ...] = (
        ForwardingAggregate.WINDOW_1D,
        ForwardingAggregate.WINDOW_7D,
        ForwardingAggregate.WINDOW_30D,
    ),
) -> int:
    """Compute forwarding aggregates and upsert per channel/window (idempotent)."""
    now = timezone.now()
    window_anchor = now.replace(minute=0, second=0, microsecond=0)
    upserted = 0

    for window in windows:
        if window not in WINDOW_TO_DELTA:
            continue
        window_start = window_anchor - WINDOW_TO_DELTA[window]

        fail_counts = {}
        failed_qs = (
            FailedHTLCs.objects.filter(timestamp__gte=window_start, timestamp__lt=now)
            .values("chan_id_out")
            .annotate(fail_count=Count("id"))
        )
        async for row in failed_qs:
            fail_counts[row["chan_id_out"]] = row["fail_count"]

        forward_qs = (
            Forwards.objects.filter(forward_date__gte=window_start, forward_date__lt=now)
            .values("chan_id_out")
            .annotate(
                in_msat=Coalesce(Sum("amt_in_msat"), 0),
                out_msat=Coalesce(Sum("amt_out_msat"), 0),
                fee_sum=Coalesce(Sum("fee"), 0.0),
                forward_count=Count("id"),
            )
        )

        seen_chan_ids: set[str] = set()
        async for row in forward_qs:
            chan_id = row["chan_id_out"]
            seen_chan_ids.add(chan_id)
            await ForwardingAggregate.objects.aupdate_or_create(
                window=window,
                channel_id=chan_id,
                window_start=window_start,
                defaults={
                    "in_msat": row["in_msat"],
                    "out_msat": row["out_msat"],
                    "fees_msat": _fee_sat_to_msat(row["fee_sum"]),
                    "forward_count": row["forward_count"],
                    "fail_count": fail_counts.get(chan_id, 0),
                },
            )
            upserted += 1

        for chan_id, fail_count in fail_counts.items():
            if chan_id in seen_chan_ids:
                continue
            await ForwardingAggregate.objects.aupdate_or_create(
                window=window,
                channel_id=chan_id,
                window_start=window_start,
                defaults={
                    "in_msat": 0,
                    "out_msat": 0,
                    "fees_msat": 0,
                    "forward_count": 0,
                    "fail_count": fail_count,
                },
            )
            upserted += 1

    return upserted
