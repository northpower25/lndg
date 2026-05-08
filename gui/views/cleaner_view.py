from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from lndg import settings
from .utils import is_login_required
from gui.models import UserMode
from gui.jobs.cleaner import (
    DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS,
    DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS,
    DEFAULT_CHANGELOG_RETENTION_DAYS,
    DEFAULT_BACKUP_LOG_RETENTION_DAYS,
    DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS,
    DEFAULT_POLICYRUN_RETENTION_DAYS,
    DEFAULT_RECOMMENDATION_RETENTION_DAYS,
    DEFAULT_SPLICE_LOG_RETENTION_DAYS,
    DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS,
    DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS,
)


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/maintenance/'), settings.LOGIN_REQUIRED)
def cleaner_view(request):
    """Render the Data Maintenance / Cleaner settings page (expert/advanced mode)."""
    user_mode_obj = UserMode.load()

    # Read current retention settings from LocalSettings, with defaults
    from gui.models import LocalSettings

    def _int_setting(key: str, default: int) -> int:
        qs = LocalSettings.objects.filter(key=key)
        if qs.exists():
            try:
                return int(qs.first().value)
            except (ValueError, TypeError):
                pass
        return default

    retention = {
        "channel_snapshots": _int_setting(
            "RETAIN-Snapshots", DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS
        ),
        "forwarding_aggregates": _int_setting(
            "RETAIN-FwdAgg", DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS
        ),
        "change_log": _int_setting("RETAIN-ChangeLog", DEFAULT_CHANGELOG_RETENTION_DAYS),
        "backup_log": _int_setting("RETAIN-BackupLog", DEFAULT_BACKUP_LOG_RETENTION_DAYS),
        "failed_payments": _int_setting(
            "RETAIN-Payments", DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS
        ),
        "recommendations": _int_setting(
            "RETAIN-Recommendations", DEFAULT_RECOMMENDATION_RETENTION_DAYS
        ),
        "policy_runs": _int_setting(
            "RETAIN-PolicyRuns", DEFAULT_POLICYRUN_RETENTION_DAYS
        ),
        "splice_log": _int_setting(
            "RETAIN-SpliceLog", DEFAULT_SPLICE_LOG_RETENTION_DAYS
        ),
        "rebalance_ml_records": _int_setting(
            "RETAIN-RebalanceMLRecords", DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS
        ),
        "autofee_ml_records": _int_setting(
            "RETAIN-AutoFeeMLRecords", DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS
        ),
    }

    context = {
        "user_mode": user_mode_obj.mode,
        "retention": retention,
    }
    return render(request, "cleaner.html", context)
