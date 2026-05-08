from __future__ import annotations

from datetime import timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone

from gui.models import (
    AutoFeeMLRecord,
    BackupLog,
    ChannelSnapshot,
    ChangeLog,
    ForwardingAggregate,
    PolicyRun,
    RebalanceMLRecord,
    Recommendation,
    SpliceLog,
)

DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS = 90
DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS = 180
DEFAULT_CHANGELOG_RETENTION_DAYS = 365
DEFAULT_BACKUP_LOG_RETENTION_DAYS = 90
DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS = 90
DEFAULT_RECOMMENDATION_RETENTION_DAYS = 90
DEFAULT_POLICYRUN_RETENTION_DAYS = 90
DEFAULT_SPLICE_LOG_RETENTION_DAYS = 365
DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS = 180
DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS = 180


async def _delete_older_than(
    queryset, cutoff, *, time_field: str = "timestamp", batch_size: int = 5000
) -> int:
    total_deleted = 0
    while True:
        filter_kwargs = {f"{time_field}__lt": cutoff}
        ids = [
            obj_id
            async for obj_id in queryset.filter(**filter_kwargs).values_list("id", flat=True)[
                :batch_size
            ]
        ]
        if not ids:
            break
        deleted, _ = await sync_to_async(
            queryset.model.objects.filter(id__in=ids).delete
        )()
        total_deleted += deleted
    return total_deleted


async def clean_channel_snapshots(retention_days: int = DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(ChannelSnapshot.objects, cutoff)


async def clean_forwarding_aggregates(
    retention_days: int = DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS,
) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(
        ForwardingAggregate.objects, cutoff, time_field="window_start"
    )


async def clean_change_log(retention_days: int = DEFAULT_CHANGELOG_RETENTION_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(ChangeLog.objects, cutoff)


async def clean_backup_log(retention_days: int = DEFAULT_BACKUP_LOG_RETENTION_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(BackupLog.objects, cutoff, time_field="created_at")


async def clean_failed_payments(
    retention_days: int = DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS,
) -> int:
    """Delete failed and in-flight payment records older than *retention_days*.

    Integrates the existing ``clean_failed_payments`` view logic so that it
    can be triggered both manually (via the API endpoint) and by the scheduled
    retention job.  Records with status 1 (in-flight / HTLC_INFLIGHT) or
    status 3 (failed / FAILED) that were created more than *retention_days*
    ago are removed.
    """
    from gui.models import Payments

    # Status values: 1 = in-flight (HTLC_INFLIGHT), 3 = failed (FAILED)
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(
        Payments.objects.filter(status__in=[1, 3]),
        cutoff,
        time_field="creation_date",
    )


async def clean_recommendations(
    retention_days: int = DEFAULT_RECOMMENDATION_RETENTION_DAYS,
) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(Recommendation.objects, cutoff, time_field="created_at")


async def clean_policy_runs(retention_days: int = DEFAULT_POLICYRUN_RETENTION_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(PolicyRun.objects, cutoff, time_field="executed_at")


async def clean_splice_log(retention_days: int = DEFAULT_SPLICE_LOG_RETENTION_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(SpliceLog.objects, cutoff, time_field="initiated_at")


async def clean_rebalance_ml_records(
    retention_days: int = DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS,
) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(RebalanceMLRecord.objects, cutoff, time_field="timestamp")


async def clean_autofee_ml_records(
    retention_days: int = DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS,
) -> int:
    cutoff = timezone.now() - timedelta(days=retention_days)
    return await _delete_older_than(AutoFeeMLRecord.objects, cutoff, time_field="timestamp")
