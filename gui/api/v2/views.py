import datetime
import dataclasses
import json
from statistics import median as _median

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from gui.jobs.executor import execute_policy
from gui.jobs.external_integrations import classify_fee_signal, get_mempool_recommended_fees

# msats per sat – used when converting amt_out_msat → sat
_MSAT_PER_SAT = 1000


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "api_version": "v2"})


class _UserSettingsThrottle(UserRateThrottle):
    rate = "60/minute"


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
@throttle_classes([_UserSettingsThrottle])
def user_settings(request):
    """GET or PUT the current user-mode and AI-feature-flag settings."""
    from gui.models import UserMode

    instance = UserMode.load()

    _fields = [
        "mode",
        "onboarding_step",
        "onboarding_completed",
        "language",
        "ai_mode",
        "ai_explain_always",
        "ai_min_data_days",
        "ai_max_auto_actions_day",
        "ai_cooldown_minutes",
        "ai_shadow_log_enabled",
    ]

    if request.method == "GET":
        return Response({f: getattr(instance, f) for f in _fields})

    # PUT – update only provided fields
    allowed_choices = {
        "mode": [c[0] for c in UserMode.MODE_CHOICES],
        "ai_mode": [c[0] for c in UserMode.AI_MODE_CHOICES],
    }
    errors: dict = {}
    for field in _fields:
        if field not in request.data:
            continue
        value = request.data[field]
        if field in allowed_choices and value not in allowed_choices[field]:
            errors[field] = f"Must be one of {allowed_choices[field]}"
            continue
        setattr(instance, field, value)
    if errors:
        return Response({"errors": errors}, status=400)
    instance.save()
    return Response({f: getattr(instance, f) for f in _fields})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cockpit_stats(request) -> Response:
    """Return aggregated stats for the five cockpit dashboard tiles."""
    from gui.models import Channels, FailedHTLCs, Forwards

    now = timezone.now()
    cutoff_7d = now - datetime.timedelta(days=7)
    cutoff_30d = now - datetime.timedelta(days=30)
    cutoff_24h = now - datetime.timedelta(hours=24)

    # ── 1. Routing activity ──────────────────────────────────────────────────
    def _routing_stats(cutoff: datetime.datetime) -> dict:
        agg = Forwards.objects.filter(forward_date__gte=cutoff).aggregate(
            count=Count("id"),
            fees_sat=Sum("fee"),
            volume_msat=Sum("amt_out_msat"),
        )
        return {
            "count": agg["count"] or 0,
            "fees_sat": round(agg["fees_sat"] or 0, 3),
            "volume_sat": round((agg["volume_msat"] or 0) / _MSAT_PER_SAT),
        }

    routing = {
        "7d": _routing_stats(cutoff_7d),
        "30d": _routing_stats(cutoff_30d),
    }

    # ── 2. Liquidity balance ─────────────────────────────────────────────────
    open_channels = Channels.objects.filter(is_open=True)
    liq_agg = open_channels.aggregate(
        total_out=Sum("local_balance"),
        total_in=Sum("remote_balance"),
        total_cap=Sum("capacity"),
    )
    total_out = liq_agg["total_out"] or 0
    total_cap = liq_agg["total_cap"] or 0
    liquidity = {
        "total_outbound_sat": total_out,
        "total_inbound_sat": liq_agg["total_in"] or 0,
        "total_capacity_sat": total_cap,
        "outbound_pct": round(total_out * 100 / total_cap) if total_cap else 0,
    }

    # ── 3. Fee positioning ───────────────────────────────────────────────────
    fee_rates = list(open_channels.values_list("local_fee_rate", flat=True))
    avg_fee_rate = round(sum(fee_rates) / len(fee_rates)) if fee_rates else 0
    med_fee_rate = round(_median(fee_rates)) if fee_rates else 0
    fees_info = {
        "avg_fee_rate": avg_fee_rate,
        "median_fee_rate": med_fee_rate,
        "channel_count": len(fee_rates),
        "channels_above_median": sum(1 for f in fee_rates if f > med_fee_rate),
        "channels_below_median": sum(1 for f in fee_rates if f < med_fee_rate),
    }

    # ── 4. Issues ────────────────────────────────────────────────────────────
    failed_24h = FailedHTLCs.objects.filter(timestamp__gte=cutoff_24h).count()
    disabled_count = open_channels.filter(local_disabled=True).count()
    inactive_count = open_channels.filter(is_active=False).count()
    issues = {
        "failed_htlc_24h": failed_24h,
        "disabled_channels": disabled_count,
        "inactive_channels": inactive_count,
        "total_issues": failed_24h + disabled_count,
    }

    from gui.jobs.recommender import generate_recommendations

    # ── 5. Next best actions (heuristic recommender persisted in DB) ─────────
    next_actions = generate_recommendations(limit=3)

    return Response(
        {
            "routing": routing,
            "liquidity": liquidity,
            "fees": fees_info,
            "issues": issues,
            "next_actions": next_actions[:3],
        }
    )


# ── Capability Registry ────────────────────────────────────────────────────────

class _CapabilitiesThrottle(UserRateThrottle):
    rate = "120/minute"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_CapabilitiesThrottle])
def capabilities(request) -> Response:
    """Return the capability flags of the currently active backend.

    Clients should use these flags to decide which features to enable in the
    UI.  Buttons for unsupported capabilities should be disabled with an
    explanatory tooltip (R-GUI-7).
    """
    from gui.backends.registry import get_capabilities

    caps = get_capabilities()
    return Response(dataclasses.asdict(caps))


# ── Chart data APIs ────────────────────────────────────────────────────────────

class _ChartThrottle(UserRateThrottle):
    rate = "60/minute"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_ChartThrottle])
def chart_liquidity(request) -> Response:
    """Liquidity Donut – inbound vs. outbound per channel and node total.

    Returns per-channel liquidity data suitable for a donut / pie chart
    as well as aggregated node totals.

    Response shape::

        {
            "node": {"total_outbound_sat": int, "total_inbound_sat": int, "total_capacity_sat": int},
            "channels": [
                {"channel_id": str, "alias": str,
                 "local_balance_sat": int, "remote_balance_sat": int, "capacity_sat": int}
            ]
        }
    """
    from gui.models import Channels

    qs = Channels.objects.filter(is_open=True).values(
        "chan_id", "alias", "local_balance", "remote_balance", "capacity"
    )
    channels = [
        {
            "channel_id": ch["chan_id"],
            "alias": ch["alias"] or ch["chan_id"][:8],
            "local_balance_sat": ch["local_balance"],
            "remote_balance_sat": ch["remote_balance"],
            "capacity_sat": ch["capacity"],
        }
        for ch in qs
    ]
    total_out = sum(c["local_balance_sat"] for c in channels)
    total_in = sum(c["remote_balance_sat"] for c in channels)
    total_cap = sum(c["capacity_sat"] for c in channels)
    return Response(
        {
            "node": {
                "total_outbound_sat": total_out,
                "total_inbound_sat": total_in,
                "total_capacity_sat": total_cap,
            },
            "channels": channels,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_ChartThrottle])
def chart_channel_health(request) -> Response:
    """Channel Health Heatmap – time vs. channel based on ChannelSnapshot.

    Query parameters:
        channel_id (optional): filter to a single channel.
        days (optional, default 7): number of past days to include.

    Response shape::

        {
            "snapshots": [
                {"timestamp": ISO8601, "channel_id": str,
                 "local_balance_sat": int, "remote_balance_sat": int,
                 "capacity_sat": int, "is_active": bool}
            ]
        }
    """
    from gui.models import ChannelSnapshot

    days = int(request.query_params.get("days", 7))
    since = timezone.now() - datetime.timedelta(days=days)
    qs = ChannelSnapshot.objects.filter(timestamp__gte=since).order_by("timestamp")
    channel_id = request.query_params.get("channel_id")
    if channel_id:
        qs = qs.filter(channel_id=channel_id)
    snapshots = list(
        qs.values(
            "timestamp", "channel_id", "local_balance_sat",
            "remote_balance_sat", "capacity_sat", "is_active",
        )
    )
    for s in snapshots:
        s["timestamp"] = s["timestamp"].isoformat()
    return Response({"snapshots": snapshots})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_ChartThrottle])
def chart_fee_volume(request) -> Response:
    """Fee vs. Volume Scatter – fee elasticity from Forwards and FeeLog.

    Query parameters:
        days (optional, default 30): number of past days to include.

    Response shape::

        {
            "points": [
                {"channel_id": str, "alias": str,
                 "fee_rate_ppm": int, "volume_sat": int, "fees_sat": float}
            ]
        }
    """
    from gui.models import Channels, Forwards

    days = int(request.query_params.get("days", 30))
    since = timezone.now() - datetime.timedelta(days=days)

    fwd_agg = (
        Forwards.objects.filter(forward_date__gte=since)
        .values("chan_id_out")
        .annotate(
            volume_msat=Sum("amt_out_msat"),
            fees_sat_sum=Sum("fee"),
            count=Count("id"),
        )
    )
    channel_map = {
        ch["chan_id"]: ch
        for ch in Channels.objects.filter(is_open=True).values(
            "chan_id", "alias", "local_fee_rate"
        )
    }
    points = []
    for row in fwd_agg:
        cid = row["chan_id_out"]
        ch = channel_map.get(cid, {})
        points.append(
            {
                "channel_id": cid,
                "alias": ch.get("alias") or cid[:8],
                "fee_rate_ppm": ch.get("local_fee_rate", 0),
                "volume_sat": round((row["volume_msat"] or 0) / _MSAT_PER_SAT),
                "fees_sat": round(row["fees_sat_sum"] or 0, 3),
                "forward_count": row["count"],
            }
        )
    return Response({"points": points})


# ── Cleaner ────────────────────────────────────────────────────────────────────

class _CleanerThrottle(UserRateThrottle):
    rate = "10/minute"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_CleanerThrottle])
def cleaner_run(request) -> Response:
    """Manually trigger the DB retention cleaner.

    Two modes:

    **Single-table mode** (backward-compatible)::

        {
            "table": "channel_snapshots" | "forwarding_aggregates" | "change_log"
                     | "backup_log" | "failed_payments" | "recommendations"
                     | "policy_runs" | "splice_log"
                     | "rebalance_ml_records" | "autofee_ml_records",
            "retention_days": int  (optional – uses per-table LocalSettings/defaults)
        }

    **All-tables mode** (used by the Maintenance UI)::

        {"dry_run": true | false}

    When ``dry_run`` is ``true`` (the safe default) the endpoint returns a
    *count* of rows that *would* be deleted without actually removing them.
    """
    from asgiref.sync import async_to_sync
    from gui.jobs.cleaner import (
        clean_backup_log,
        clean_channel_snapshots,
        clean_change_log,
        clean_failed_payments,
        clean_forwarding_aggregates,
        clean_policy_runs,
        clean_rebalance_ml_records,
        clean_recommendations,
        clean_splice_log,
        clean_autofee_ml_records,
        DEFAULT_BACKUP_LOG_RETENTION_DAYS,
        DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS,
        DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS,
        DEFAULT_CHANGELOG_RETENTION_DAYS,
        DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS,
        DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS,
        DEFAULT_POLICYRUN_RETENTION_DAYS,
        DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS,
        DEFAULT_RECOMMENDATION_RETENTION_DAYS,
        DEFAULT_SPLICE_LOG_RETENTION_DAYS,
    )

    # ── All-tables mode ─────────────────────────────────────────────────────
    if "table" not in request.data:
        dry_run: bool = bool(request.data.get("dry_run", True))

        def _retention(ls_key: str, default: int) -> int:
            from gui.models import LocalSettings
            qs = LocalSettings.objects.filter(key=ls_key)
            if qs.exists():
                try:
                    return int(qs.first().value)
                except (ValueError, TypeError):
                    pass
            return default

        snap_days = _retention("RETAIN-Snapshots", DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS)
        agg_days = _retention("RETAIN-FwdAgg", DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS)
        log_days = _retention("RETAIN-ChangeLog", DEFAULT_CHANGELOG_RETENTION_DAYS)
        bkp_days = _retention("RETAIN-BackupLog", DEFAULT_BACKUP_LOG_RETENTION_DAYS)
        pay_days = _retention("RETAIN-Payments", DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS)
        rec_days = _retention("RETAIN-Recommendations", DEFAULT_RECOMMENDATION_RETENTION_DAYS)
        run_days = _retention("RETAIN-PolicyRuns", DEFAULT_POLICYRUN_RETENTION_DAYS)
        spl_days = _retention("RETAIN-SpliceLog", DEFAULT_SPLICE_LOG_RETENTION_DAYS)
        rml_days = _retention("RETAIN-RebalanceMLRecords", DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS)
        aml_days = _retention("RETAIN-AutoFeeMLRecords", DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS)

        if dry_run:
            # Count rows that would be deleted (read-only)
            from datetime import timedelta
            from django.utils import timezone
            from gui.models import (
                BackupLog,
                ChannelSnapshot,
                ChangeLog,
                ForwardingAggregate,
                Payments,
                PolicyRun,
                RebalanceMLRecord,
                Recommendation,
                SpliceLog,
                AutoFeeMLRecord,
            )
            now = timezone.now()
            results = {
                "channel_snapshots": ChannelSnapshot.objects.filter(timestamp__lt=now - timedelta(days=snap_days)).count(),
                "forwarding_aggregates": ForwardingAggregate.objects.filter(window_start__lt=now - timedelta(days=agg_days)).count(),
                "change_log": ChangeLog.objects.filter(timestamp__lt=now - timedelta(days=log_days)).count(),
                "backup_log": BackupLog.objects.filter(created_at__lt=now - timedelta(days=bkp_days)).count(),
                "failed_payments": Payments.objects.filter(status__in=[1, 3], creation_date__lt=now - timedelta(days=pay_days)).count(),
                "recommendations": Recommendation.objects.filter(created_at__lt=now - timedelta(days=rec_days)).count(),
                "policy_runs": PolicyRun.objects.filter(executed_at__lt=now - timedelta(days=run_days)).count(),
                "splice_log": SpliceLog.objects.filter(initiated_at__lt=now - timedelta(days=spl_days)).count(),
                "rebalance_ml_records": RebalanceMLRecord.objects.filter(timestamp__lt=now - timedelta(days=rml_days)).count(),
                "autofee_ml_records": AutoFeeMLRecord.objects.filter(timestamp__lt=now - timedelta(days=aml_days)).count(),
            }
        else:
            results = {
                "channel_snapshots": async_to_sync(clean_channel_snapshots)(retention_days=snap_days),
                "forwarding_aggregates": async_to_sync(clean_forwarding_aggregates)(retention_days=agg_days),
                "change_log": async_to_sync(clean_change_log)(retention_days=log_days),
                "backup_log": async_to_sync(clean_backup_log)(retention_days=bkp_days),
                "failed_payments": async_to_sync(clean_failed_payments)(retention_days=pay_days),
                "recommendations": async_to_sync(clean_recommendations)(retention_days=rec_days),
                "policy_runs": async_to_sync(clean_policy_runs)(retention_days=run_days),
                "splice_log": async_to_sync(clean_splice_log)(retention_days=spl_days),
                "rebalance_ml_records": async_to_sync(clean_rebalance_ml_records)(retention_days=rml_days),
                "autofee_ml_records": async_to_sync(clean_autofee_ml_records)(retention_days=aml_days),
            }
        return Response({"dry_run": dry_run, "results": results})

    # ── Single-table mode (backward-compatible) ─────────────────────────────
    table = request.data.get("table", "")
    retention_days = request.data.get("retention_days")

    dispatch: dict = {
        "channel_snapshots": (clean_channel_snapshots, DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS),
        "forwarding_aggregates": (clean_forwarding_aggregates, DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS),
        "change_log": (clean_change_log, DEFAULT_CHANGELOG_RETENTION_DAYS),
        "backup_log": (clean_backup_log, DEFAULT_BACKUP_LOG_RETENTION_DAYS),
        "failed_payments": (clean_failed_payments, DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS),
        "recommendations": (clean_recommendations, DEFAULT_RECOMMENDATION_RETENTION_DAYS),
        "policy_runs": (clean_policy_runs, DEFAULT_POLICYRUN_RETENTION_DAYS),
        "splice_log": (clean_splice_log, DEFAULT_SPLICE_LOG_RETENTION_DAYS),
        "rebalance_ml_records": (clean_rebalance_ml_records, DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS),
        "autofee_ml_records": (clean_autofee_ml_records, DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS),
    }
    if table not in dispatch:
        return Response(
            {"error": f"Unknown table '{table}'. Choose from: {list(dispatch)}."},
            status=400,
        )
    fn, default_days = dispatch[table]
    if retention_days is not None:
        try:
            days = int(retention_days)
        except (TypeError, ValueError):
            return Response({"error": "retention_days must be a positive integer."}, status=400)
        if days < 1 or days > 3650:
            return Response({"error": "retention_days must be between 1 and 3650."}, status=400)
    else:
        days = default_days
    deleted = async_to_sync(fn)(retention_days=days)
    return Response({"table": table, "retention_days": days, "deleted": deleted})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_CleanerThrottle])
def cleaner_settings(request) -> Response:
    """Save retention-period overrides to LocalSettings.

    Request body (JSON)::

        {
            "retention_channel_snapshots":    int,
            "retention_forwarding_aggregates": int,
            "retention_change_log":            int,
            "retention_backup_log":            int,
            "retention_failed_payments":       int,
            "retention_recommendations":       int,
            "retention_policy_runs":           int,
            "retention_splice_log":            int,
            "retention_rebalance_ml_records":  int,
            "retention_autofee_ml_records":    int
        }

    All fields are optional; only provided fields are updated.
    """
    from gui.models import LocalSettings
    from gui.jobs.cleaner import (
        DEFAULT_BACKUP_LOG_RETENTION_DAYS,
        DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS,
        DEFAULT_CHANGELOG_RETENTION_DAYS,
        DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS,
        DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS,
        DEFAULT_POLICYRUN_RETENTION_DAYS,
        DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS,
        DEFAULT_RECOMMENDATION_RETENTION_DAYS,
        DEFAULT_SPLICE_LOG_RETENTION_DAYS,
        DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS,
    )

    key_map = {
        "retention_channel_snapshots": ("RETAIN-Snapshots", DEFAULT_CHANNEL_SNAPSHOT_RETENTION_DAYS),
        "retention_forwarding_aggregates": ("RETAIN-FwdAgg", DEFAULT_FORWARDING_AGGREGATE_RETENTION_DAYS),
        "retention_change_log": ("RETAIN-ChangeLog", DEFAULT_CHANGELOG_RETENTION_DAYS),
        "retention_backup_log": ("RETAIN-BackupLog", DEFAULT_BACKUP_LOG_RETENTION_DAYS),
        "retention_failed_payments": ("RETAIN-Payments", DEFAULT_FAILED_PAYMENTS_RETENTION_DAYS),
        "retention_recommendations": ("RETAIN-Recommendations", DEFAULT_RECOMMENDATION_RETENTION_DAYS),
        "retention_policy_runs": ("RETAIN-PolicyRuns", DEFAULT_POLICYRUN_RETENTION_DAYS),
        "retention_splice_log": ("RETAIN-SpliceLog", DEFAULT_SPLICE_LOG_RETENTION_DAYS),
        "retention_rebalance_ml_records": ("RETAIN-RebalanceMLRecords", DEFAULT_REBALANCE_ML_RECORD_RETENTION_DAYS),
        "retention_autofee_ml_records": ("RETAIN-AutoFeeMLRecords", DEFAULT_AUTOFEE_ML_RECORD_RETENTION_DAYS),
    }
    saved = {}
    errors = {}
    for field, (ls_key, _default) in key_map.items():
        if field not in request.data:
            continue
        try:
            v = int(request.data[field])
            if v < 1 or v > 3650:
                errors[field] = "Must be between 1 and 3650."
                continue
        except (TypeError, ValueError):
            errors[field] = "Must be a positive integer."
            continue
        obj, _ = LocalSettings.objects.update_or_create(key=ls_key, defaults={"value": str(v)})
        saved[field] = v
    if errors:
        return Response({"errors": errors, "saved": saved}, status=400)
    return Response({"saved": saved})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cleaner_counts(request) -> Response:
    """Return approximate row counts for all managed time-series tables."""
    from gui.models import (
        BackupLog,
        ChannelSnapshot,
        ChangeLog,
        ForwardingAggregate,
        Payments,
        PolicyRun,
        RebalanceMLRecord,
        Recommendation,
        SpliceLog,
        AutoFeeMLRecord,
    )

    return Response({
        "channel_snapshots": ChannelSnapshot.objects.count(),
        "forwarding_aggregates": ForwardingAggregate.objects.count(),
        "change_log": ChangeLog.objects.count(),
        "backup_log": BackupLog.objects.count(),
        "failed_payments": Payments.objects.filter(status__in=[1, 3]).count(),
        "recommendations": Recommendation.objects.count(),
        "policy_runs": PolicyRun.objects.count(),
        "splice_log": SpliceLog.objects.count(),
        "rebalance_ml_records": RebalanceMLRecord.objects.count(),
        "autofee_ml_records": AutoFeeMLRecord.objects.count(),
    })


# ── Recommendations / Policies / Splice ────────────────────────────────────────

class _RecommendationThrottle(UserRateThrottle):
    rate = "30/minute"


class _PolicyRunThrottle(UserRateThrottle):
    rate = "10/minute"


class _SpliceThrottle(UserRateThrottle):
    rate = "20/minute"


def _to_int(value, *, minimum: int | None = None, maximum: int | None = None) -> int:
    parsed = int(value)
    if minimum is not None and parsed < minimum:
        raise ValueError("below_minimum")
    if maximum is not None and parsed > maximum:
        raise ValueError("above_maximum")
    return parsed


def _validate_trigger_data_shape(trigger_data: dict) -> bool:
    if len(trigger_data) > 50:
        return False
    try:
        encoded = json.dumps(trigger_data)
    except (TypeError, ValueError):
        return False
    return len(encoded) <= 4096


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_RecommendationThrottle])
def recommendation_dry_run(request, recommendation_id: int) -> Response:
    from gui.models import Recommendation

    recommendation = Recommendation.objects.filter(pk=recommendation_id).first()
    if recommendation is None:
        return Response({"error": _("Recommendation not found.")}, status=404)
    now = timezone.now().isoformat()
    recommendation.dry_run_result = {
        "simulate": True,
        "executed_at": now,
        "estimate": {
            "expected_effect": _("No write action executed. Dry-run only."),
            "risk_level": recommendation.risk_level,
            "confidence": recommendation.confidence,
        },
    }
    recommendation.save(update_fields=["dry_run_result"])
    return Response({"status": "ok", "recommendation_id": recommendation.id, "dry_run_result": recommendation.dry_run_result})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_PolicyRunThrottle])
def policy_run(request, policy_id: int) -> Response:
    simulate = bool(request.data.get("simulate", True))
    trigger_data = request.data.get("trigger_data") or {}
    if not isinstance(trigger_data, dict):
        return Response({"error": _("trigger_data must be an object.")}, status=400)
    if not _validate_trigger_data_shape(trigger_data):
        return Response({"error": _("trigger_data is too large or invalid.")}, status=400)
    result = execute_policy(
        policy_id=policy_id,
        simulate=simulate,
        trigger_data=trigger_data,
    )
    if not result["ok"]:
        return Response({"error": _("Policy not found.")}, status=404)
    return Response(
        {
            "status": result["status"],
            "policy_run_id": result["policy_run_id"],
            "was_dry_run": result["was_dry_run"],
            "outcome": result["outcome"],
            "actions_taken": result["actions_taken"],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_SpliceThrottle])
def splice_preview(request, channel_id: str) -> Response:
    from gui.models import Channels
    from gui.models import NotificationSettings

    channel = Channels.objects.filter(chan_id=channel_id, is_open=True).first()
    if channel is None:
        return Response({"error": _("Channel not found.")}, status=404)
    amount_sat = request.query_params.get("amount_sat", "0")
    fee_rate = request.query_params.get("fee_rate", "5")
    try:
        parsed_amount = _to_int(amount_sat, minimum=0, maximum=10_000_000_000)
        parsed_fee_rate = _to_int(fee_rate, minimum=1, maximum=5000)
    except Exception:
        return Response({"error": _("Invalid amount_sat or fee_rate.")}, status=400)

    estimated_fee_sat = max(1, int(parsed_fee_rate * 120))
    projected_capacity = (channel.capacity or 0) + parsed_amount
    cfg = NotificationSettings.load()
    fee_payload = get_mempool_recommended_fees(enabled=cfg.mempool_enabled)
    fee_signal = classify_fee_signal(fee_payload)
    return Response(
        {
            "channel_id": channel_id,
            "amount_sat": parsed_amount,
            "estimated_on_chain_fee_sat": estimated_fee_sat,
            "projected_capacity_sat": projected_capacity,
            "routing_impact": _("Temporary routing degradation while splice confirms."),
            "risk_label": "medium",
            "mempool_fee_signal": None if fee_signal is None else {
                "light": fee_signal.light,
                "label": fee_signal.label,
                "wait_window": fee_signal.wait_window,
                "hour_fee": fee_payload.get("hourFee"),
            },
        }
    )


def _resolve_recommendation_id(request_data) -> int | None:
    recommendation_id = request_data.get("recommendation_id")
    if recommendation_id in (None, ""):
        return None
    return int(recommendation_id)


def _require_splice_capability():
    from gui.backends.registry import get_active_backend, get_capabilities

    caps = get_capabilities()
    if not caps.can_splice:
        return caps, Response(
            {"error": _("Backend does not support channel splicing."), "can_splice": False},
            status=400,
        )
    if get_active_backend() is None:
        return caps, Response({"error": _("No active backend configured.")}, status=500)
    return caps, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_SpliceThrottle])
def splice_in(request, channel_id: str) -> Response:
    from gui.models import ChangeLog, Recommendation, SpliceLog

    _caps, error_response = _require_splice_capability()
    if error_response is not None:
        return error_response
    from gui.jobs.executor import execute_splice_in
    try:
        amount_sat = _to_int(request.data.get("amount_sat"), minimum=1, maximum=10_000_000_000)
        fee_rate = _to_int(request.data.get("fee_rate", 5), minimum=1, maximum=5000)
        recommendation_id = _resolve_recommendation_id(request.data)
    except Exception:
        return Response({"error": _("Invalid request payload.")}, status=400)

    recommendation = Recommendation.objects.filter(pk=recommendation_id).first() if recommendation_id else None
    try:
        action = execute_splice_in(channel_id=channel_id, amount_sat=amount_sat, fee_rate=fee_rate)
    except Exception as exc:
        import logging as _logging

        _logging.getLogger(__name__).error("Splice in failed for %s: %s", channel_id, exc, exc_info=True)
        return Response({"error": _("Splice in failed.")}, status=400)
    status = SpliceLog.STATUS_PENDING
    txid = ""
    if getattr(action, "txid", None):
        txid = action.txid
        status = SpliceLog.STATUS_BROADCAST

    splice_log = SpliceLog.objects.create(
        channel_id=channel_id,
        splice_type=SpliceLog.TYPE_IN,
        amount_sat=amount_sat,
        on_chain_fee_sat=max(1, fee_rate * 120),
        status=status,
        txid=txid,
        rationale={
            "requested_by": "manual",
            "recommendation_id": recommendation.id if recommendation else None,
        },
        recommendation=recommendation,
    )
    ChangeLog.objects.create(
        change_type='splice_in',
        target_channel_id=channel_id,
        actor='manual',
        old_value={},
        new_value={"amount_sat": amount_sat, "fee_rate": fee_rate, "splice_log_id": splice_log.id},
        rationale={"risk_label": "medium"},
    )
    return Response({"status": "ok", "splice_log_id": splice_log.id, "channel_id": channel_id, "txid": txid})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_SpliceThrottle])
def splice_out(request, channel_id: str) -> Response:
    from gui.models import ChangeLog, Recommendation, SpliceLog

    _caps, error_response = _require_splice_capability()
    if error_response is not None:
        return error_response
    from gui.jobs.executor import execute_splice_out
    try:
        amount_sat = _to_int(request.data.get("amount_sat"), minimum=1, maximum=10_000_000_000)
        fee_rate = _to_int(request.data.get("fee_rate", 5), minimum=1, maximum=5000)
        destination = str(request.data.get("destination", "")).strip()
        recommendation_id = _resolve_recommendation_id(request.data)
    except Exception:
        return Response({"error": _("Invalid request payload.")}, status=400)
    if not destination:
        return Response({"error": _("destination is required for splice out.")}, status=400)

    recommendation = Recommendation.objects.filter(pk=recommendation_id).first() if recommendation_id else None
    try:
        action = execute_splice_out(
            channel_id=channel_id,
            amount_sat=amount_sat,
            destination=destination,
            fee_rate=fee_rate,
        )
    except Exception as exc:
        import logging as _logging

        _logging.getLogger(__name__).error("Splice out failed for %s: %s", channel_id, exc, exc_info=True)
        return Response({"error": _("Splice out failed.")}, status=400)
    status = SpliceLog.STATUS_PENDING
    txid = ""
    if getattr(action, "txid", None):
        txid = action.txid
        status = SpliceLog.STATUS_BROADCAST

    splice_log = SpliceLog.objects.create(
        channel_id=channel_id,
        splice_type=SpliceLog.TYPE_OUT,
        amount_sat=amount_sat,
        on_chain_fee_sat=max(1, fee_rate * 120),
        status=status,
        txid=txid,
        rationale={
            "requested_by": "manual",
            "destination": destination,
            "recommendation_id": recommendation.id if recommendation else None,
        },
        recommendation=recommendation,
    )
    ChangeLog.objects.create(
        change_type='splice_out',
        target_channel_id=channel_id,
        actor='manual',
        old_value={},
        new_value={
            "amount_sat": amount_sat,
            "destination": destination,
            "fee_rate": fee_rate,
            "splice_log_id": splice_log.id,
        },
        rationale={"risk_label": "high"},
    )
    return Response({"status": "ok", "splice_log_id": splice_log.id, "channel_id": channel_id, "txid": txid})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_SpliceThrottle])
def splice_status(request, channel_id: str) -> Response:
    from gui.models import SpliceLog

    splice_id = request.query_params.get("splice_id")
    if splice_id:
        item = SpliceLog.objects.filter(pk=splice_id, channel_id=channel_id).first()
    else:
        item = SpliceLog.objects.filter(channel_id=channel_id).order_by("-initiated_at").first()
    if item is None:
        return Response({"error": _("No splice operation found for this channel.")}, status=404)
    return Response(
        {
            "splice_id": item.id,
            "channel_id": item.channel_id,
            "splice_type": item.splice_type,
            "status": item.status,
            "txid": item.txid,
            "amount_sat": item.amount_sat,
            "on_chain_fee_sat": item.on_chain_fee_sat,
            "initiated_at": item.initiated_at.isoformat(),
            "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None,
            "rationale": item.rationale,
        }
    )


# ── Backup ─────────────────────────────────────────────────────────────────────

class _BackupThrottle(UserRateThrottle):
    rate = "5/minute"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_BackupThrottle])
def backup_create(request) -> Response:
    """Trigger a backup of the requested type.

    Request body (JSON)::

        {"type": "settings" | "database"}

    Returns metadata about the created backup including its ID, path, and checksum.
    """
    from gui.jobs.backup import run_backup

    backup_type = request.data.get("type", "settings")
    if backup_type not in ("settings", "database"):
        return Response({"error": "type must be 'settings' or 'database'"}, status=400)

    try:
        log = run_backup(backup_type=backup_type, actor="manual")
        return Response(
            {
                "id": log.pk,
                "backup_type": log.backup_type,
                "status": log.status,
                "file_size_bytes": log.file_size_bytes,
                "checksum": log.checksum,
                "created_at": log.created_at.isoformat(),
            }
        )
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error("Backup creation failed: %s", exc, exc_info=True)
        return Response({"error": "Backup creation failed. See server logs for details."}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([_BackupThrottle])
def backup_list(request) -> Response:
    """List recent backups (most recent first, limit 50)."""
    from gui.models import BackupLog

    qs = BackupLog.objects.order_by("-created_at")[:50]
    return Response(
        [
            {
                "id": b.pk,
                "backup_type": b.backup_type,
                "status": b.status,
                "file_size_bytes": b.file_size_bytes,
                "checksum": b.checksum,
                "created_at": b.created_at.isoformat(),
                "actor": b.actor,
            }
            for b in qs
        ]
    )


class _RestoreThrottle(UserRateThrottle):
    rate = "3/minute"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([_RestoreThrottle])
def backup_restore(request) -> Response:
    """Restore from a previously created backup file.

    Accepts a multipart/form-data POST with:
        backup_file       – the backup file to restore
        expected_checksum – SHA-256 hex digest of the uploaded file
        dry_run           – 'true' | 'false' (default: 'true')

    For ``dry_run=true`` the endpoint validates the file and returns which
    tables / keys would be affected without making any changes.

    For ``dry_run=false`` (settings type only):
        1. Creates an automatic safety backup (R-SEC-6).
        2. Validates the SHA-256 checksum.
        3. Writes the settings back.

    Returns::

        {"status": "ok", "auto_backup_id": int, "tables_affected": [...]}
        {"status": "preview", "tables_affected": [...]}
    """
    import hashlib
    import json as _json
    import logging as _logging

    logger = _logging.getLogger(__name__)

    if "backup_file" not in request.FILES:
        return Response({"error": "No backup_file provided."}, status=400)

    uploaded = request.FILES["backup_file"]
    expected_checksum: str = (request.data.get("expected_checksum") or "").strip().lower()
    dry_run: bool = (request.data.get("dry_run", "true")).lower() != "false"

    # ── Validate checksum ──────────────────────────────────────────────────
    file_bytes: bytes = uploaded.read()
    actual_checksum = hashlib.sha256(file_bytes).hexdigest()
    if expected_checksum and actual_checksum != expected_checksum:
        return Response(
            {
                "error": "Checksum mismatch. Expected "
                f"{expected_checksum!r}, got {actual_checksum!r}."
            },
            status=400,
        )

    # ── Determine backup type from filename ───────────────────────────────
    filename: str = uploaded.name or ""
    if filename.startswith("settings_") or filename.endswith(".json"):
        backup_type = "settings"
    else:
        backup_type = "database"

    # ── Parse settings payload ────────────────────────────────────────────
    if backup_type == "settings":
        try:
            payload: dict = _json.loads(file_bytes.decode("utf-8"))
        except _json.JSONDecodeError:
            return Response({"error": "Invalid settings backup: file is not valid JSON."}, status=400)
        except UnicodeDecodeError:
            return Response({"error": "Invalid settings backup: backup file encoding is not UTF-8."}, status=400)
        tables_affected = list(payload.keys())
    else:
        tables_affected = ["database"]

    if dry_run:
        return Response({"status": "preview", "tables_affected": tables_affected})

    # ── Live restore (settings only; database restore requires manual process) ──
    if backup_type != "settings":
        return Response(
            {
                "error": (
                    "Live database restore is not supported via the API. "
                    "Use dry_run=true to preview. Restore the database file manually."
                )
            },
            status=400,
        )

    # ── Auto-backup before restore (R-SEC-6) ──────────────────────────────
    from gui.jobs.backup import run_backup

    auto_backup_id: int | None = None
    try:
        auto_log = run_backup(backup_type="settings", actor="pre-restore-auto")
        auto_backup_id = auto_log.pk
    except Exception as exc:
        logger.error("Pre-restore auto-backup failed: %s", exc, exc_info=True)
        return Response(
            {"error": "Safety auto-backup before restore failed. Restore aborted. See server logs."},
            status=500,
        )

    # ── Apply settings ────────────────────────────────────────────────────
    try:
        from lndg import settings as _s
        from gui.models import LocalSettings

        _safe_keys = {
            "LND_RPC_SERVER",
            "LND_MACAROON_PATH",
            "LND_TLS_PATH",
            "LND_MAX_MESSAGE",
            "LOGIN_REQUIRED",
            "TIME_ZONE",
            "LANGUAGE_CODE",
        }
        applied: list[str] = []
        for key, value in payload.items():
            if key in _safe_keys and value is not None:
                setattr(_s, key, value)
                applied.append(key)

        # Persist known keys to LocalSettings for LND connection overrides
        _lnd_key_map = {
            "LND_RPC_SERVER": "LND-RPC-Server",
            "LND_MACAROON_PATH": "LND-Macaroon",
            "LND_TLS_PATH": "LND-TLS",
        }
        for django_key, db_key in _lnd_key_map.items():
            if django_key in payload and payload[django_key] is not None:
                LocalSettings.objects.update_or_create(
                    key=db_key,
                    defaults={"value": str(payload[django_key])},
                )
    except Exception as exc:
        logger.error("Settings restore failed: %s", exc, exc_info=True)
        return Response({"error": "Settings restore failed. See server logs for details."}, status=500)

    return Response(
        {
            "status": "ok",
            "auto_backup_id": auto_backup_id,
            "tables_affected": applied,
        }
    )
