from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from gui.models import Channels, FailedHTLCs, Forwards, Recommendation


@dataclass
class RecommendationDraft:
    rec_type: str
    title: str
    target_chan_id: str
    target_pubkey: str
    risk_level: str
    confidence: float
    rationale: dict


def _build_rationale(
    *,
    reasons: list[dict],
    data_window_days: int,
    confidence: float,
    confidence_label: str = Recommendation.CONFIDENCE_HEURISTIC,
    alternatives: list[str] | None = None,
    simulation_available: bool = True,
) -> dict:
    return {
        "reasons": reasons,
        "data_source": "internal",
        "data_window_days": data_window_days,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "alternatives": alternatives or [],
        "simulation_available": simulation_available,
    }


def _cached_recent_recommendations(limit: int) -> list[Recommendation]:
    cutoff = timezone.now() - timedelta(minutes=10)
    return list(
        Recommendation.objects.filter(
            status=Recommendation.STATUS_PENDING, created_at__gte=cutoff
        ).order_by("-confidence", "-created_at")[:limit]
    )


def _to_next_action(item: Recommendation) -> dict:
    rationale = item.rationale or {}
    reasons = rationale.get("reasons", [])
    top_reason = reasons[0]["value"] if reasons else ""
    return {
        "id": item.id,
        "type": item.rec_type,
        "title": rationale.get("title", "Recommendation"),
        "reason": top_reason,
        "risk": item.risk_level,
        "confidence": item.confidence,
        "confidence_label": item.confidence_label,
        "rationale": rationale,
    }


def generate_recommendations(*, limit: int = 3) -> list[dict]:
    recent = _cached_recent_recommendations(limit)
    if recent:
        return [_to_next_action(item) for item in recent]

    now = timezone.now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_14d = now - timedelta(days=14)
    cutoff_30d = now - timedelta(days=30)
    cutoff_24h = now - timedelta(hours=24)
    drafts: list[RecommendationDraft] = []

    open_channels = Channels.objects.filter(is_open=True, is_active=True)
    fwd_out_7d = (
        Forwards.objects.filter(forward_date__gte=cutoff_7d)
        .values("chan_id_out")
        .annotate(total=Count("id"), volume=Sum("amt_out_msat"))
    )
    fwd_out_30d_map = {
        row["chan_id_out"]: row
        for row in (
            Forwards.objects.filter(forward_date__gte=cutoff_30d)
            .values("chan_id_out")
            .annotate(total=Count("id"), volume=Sum("amt_out_msat"))
        )
    }
    active_out_ids = {row["chan_id_out"] for row in fwd_out_7d}

    for ch in open_channels[:25]:
        if len(drafts) >= limit:
            break
        capacity = ch.capacity or 1
        outbound_pct = int((ch.local_balance * 100) / capacity)
        inbound_pct = 100 - outbound_pct
        flow_30d = fwd_out_30d_map.get(ch.chan_id, {"total": 0, "volume": 0})

        if ch.chan_id not in active_out_ids:
            confidence = 0.76
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_FEE,
                    title=f"Fee-Check: {ch.alias or ch.chan_id[:8]}",
                    target_chan_id=ch.chan_id,
                    target_pubkey=ch.remote_pubkey,
                    risk_level=Recommendation.RISK_LOW,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "no_outbound_flow", "value": "No outbound flow in 7 days", "weight": 0.5},
                            {"rank": 2, "signal": "stagnation_window", "value": "Review window: 14 days", "weight": 0.3},
                            {"rank": 3, "signal": "fee_position", "value": f"Current local fee rate: {ch.local_fee_rate} ppm", "weight": 0.2},
                        ],
                        data_window_days=14,
                        confidence=confidence,
                        alternatives=["rebalance", "close"],
                    )
                    | {"title": f"Fee-Check: {ch.alias or ch.chan_id[:8]}"},
                )
            )
            continue

        if inbound_pct >= 80:
            confidence = 0.8
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_REBALANCE,
                    title=f"Rebalance: {ch.alias or ch.chan_id[:8]}",
                    target_chan_id=ch.chan_id,
                    target_pubkey=ch.remote_pubkey,
                    risk_level=Recommendation.RISK_LOW,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "balance_ratio", "value": f"{inbound_pct}% inbound", "weight": 0.5},
                            {"rank": 2, "signal": "outbound_capacity", "value": f"{outbound_pct}% outbound", "weight": 0.3},
                            {"rank": 3, "signal": "flow_history", "value": "Active forwarding observed", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["fee", "splice_in"],
                    )
                    | {"title": f"Rebalance: {ch.alias or ch.chan_id[:8]}"},
                )
            )
            continue

        if outbound_pct <= 15 and (flow_30d.get("total") or 0) >= 10:
            confidence = 0.84
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_SPLICE_IN,
                    title=f"Splice In: {ch.alias or ch.chan_id[:8]}",
                    target_chan_id=ch.chan_id,
                    target_pubkey=ch.remote_pubkey,
                    risk_level=Recommendation.RISK_MEDIUM,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "high_outbound_flow", "value": f"{flow_30d.get('total', 0)} forwards in 30d", "weight": 0.45},
                            {"rank": 2, "signal": "low_outbound_liquidity", "value": f"{outbound_pct}% outbound remaining", "weight": 0.35},
                            {"rank": 3, "signal": "capacity_pressure", "value": "Channel likely constrained", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["open", "rebalance"],
                    )
                    | {"title": f"Splice In: {ch.alias or ch.chan_id[:8]}"},
                )
            )
            continue

        if (flow_30d.get("total") or 0) < 3 and capacity >= 5_000_000:
            confidence = 0.7
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_SPLICE_OUT,
                    title=f"Splice Out: {ch.alias or ch.chan_id[:8]}",
                    target_chan_id=ch.chan_id,
                    target_pubkey=ch.remote_pubkey,
                    risk_level=Recommendation.RISK_MEDIUM,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "unused_capacity", "value": "Very low forwarding activity (30d)", "weight": 0.5},
                            {"rank": 2, "signal": "capacity_size", "value": f"Capacity: {capacity} sats", "weight": 0.3},
                            {"rank": 3, "signal": "efficiency", "value": "Consider reducing idle capital", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["fee", "close"],
                    )
                    | {"title": f"Splice Out: {ch.alias or ch.chan_id[:8]}"},
                )
            )

    if len(drafts) < limit:
        failed_count = FailedHTLCs.objects.filter(timestamp__gte=cutoff_24h).count()
        if failed_count >= 25:
            confidence = 0.78
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_CLOSE,
                    title="Mitigate failed HTLC spike",
                    target_chan_id="",
                    target_pubkey="",
                    risk_level=Recommendation.RISK_HIGH,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "failed_htlc_rate", "value": f"{failed_count} failed HTLCs in 24h", "weight": 0.6},
                            {"rank": 2, "signal": "routing_health", "value": "Potential route quality degradation", "weight": 0.25},
                            {"rank": 3, "signal": "stability", "value": "Investigate problematic peers/channels", "weight": 0.15},
                        ],
                        data_window_days=1,
                        confidence=confidence,
                        alternatives=["disable", "rebalance", "fee"],
                    )
                    | {"title": "Mitigate failed HTLC spike"},
                )
            )

    if len(drafts) < limit:
        concentration = (
            open_channels.values("remote_pubkey").annotate(channel_count=Count("chan_id")).order_by("-channel_count").first()
        )
        if concentration and concentration["channel_count"] >= 4:
            confidence = 0.72
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_OPEN,
                    title="Diversify peer concentration",
                    target_chan_id="",
                    target_pubkey=concentration["remote_pubkey"],
                    risk_level=Recommendation.RISK_LOW,
                    confidence=confidence,
                    rationale=_build_rationale(
                        reasons=[
                            {"rank": 1, "signal": "peer_concentration", "value": f"{concentration['channel_count']} channels to one peer", "weight": 0.6},
                            {"rank": 2, "signal": "resilience", "value": "Diversification reduces dependency risk", "weight": 0.25},
                            {"rank": 3, "signal": "routing_options", "value": "More peer diversity can increase route options", "weight": 0.15},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["rebalance"],
                    )
                    | {"title": "Diversify peer concentration"},
                )
            )

    created: list[Recommendation] = []
    for draft in sorted(drafts, key=lambda d: d.confidence, reverse=True)[:limit]:
        created.append(
            Recommendation.objects.create(
                rec_type=draft.rec_type,
                target_chan_id=draft.target_chan_id or None,
                target_pubkey=draft.target_pubkey or None,
                rationale=draft.rationale,
                confidence=draft.confidence,
                confidence_label=Recommendation.CONFIDENCE_HEURISTIC,
                risk_level=draft.risk_level,
                status=Recommendation.STATUS_PENDING,
            )
        )
    return [_to_next_action(item) for item in created]
