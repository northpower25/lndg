import datetime
from statistics import median as _median

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

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

    # ── 5. Next best actions (heuristic) ─────────────────────────────────────
    next_actions: list[dict] = []

    # a) Channels with low outbound liquidity (limit to 3 at DB level)
    for ch in open_channels.filter(is_active=True, local_disabled=False).values(
        "chan_id", "alias", "local_balance", "capacity"
    )[:3]:
        if len(next_actions) >= 3:
            break
        cap = ch["capacity"]
        if cap > 0:
            pct = ch["local_balance"] * 100 // cap
            if pct < 20:
                next_actions.append(
                    {
                        "type": "rebalance",
                        "title": f"Rebalance: {ch['alias'] or ch['chan_id'][:8]}",
                        "reason": f"Low outbound liquidity ({pct}%)",
                        "risk": "low",
                        "confidence": 0.8,
                        "confidence_label": "heuristic",
                    }
                )

    # b) Channels with no outbound routing in 7 days
    if len(next_actions) < 3:
        active_out_ids = set(
            Forwards.objects.filter(forward_date__gte=cutoff_7d)
            .values_list("chan_id_out", flat=True)
            .distinct()
        )
        for ch in (
            open_channels.filter(is_active=True, local_disabled=False)
            .exclude(chan_id__in=active_out_ids)
            .values("chan_id", "alias", "local_fee_rate")[:3]
        ):
            if len(next_actions) >= 3:
                break
            next_actions.append(
                {
                    "type": "fee_check",
                    "title": f"Fee-Check: {ch['alias'] or ch['chan_id'][:8]}",
                    "reason": "No outbound routing in 7 days",
                    "risk": "low",
                    "confidence": 0.7,
                    "confidence_label": "heuristic",
                }
            )

    if not next_actions:
        next_actions.append(
            {
                "type": "info",
                "title": "Node looks healthy",
                "reason": "No urgent actions detected",
                "risk": "none",
                "confidence": 0.6,
                "confidence_label": "heuristic",
            }
        )

    return Response(
        {
            "routing": routing,
            "liquidity": liquidity,
            "fees": fees_info,
            "issues": issues,
            "next_actions": next_actions[:3],
        }
    )
