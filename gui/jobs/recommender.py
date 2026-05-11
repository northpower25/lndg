from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from gui.jobs.external_integrations import classify_fee_signal, get_mempool_recommended_fees
from gui.models import Channels, FailedHTLCs, Forwards, NotificationSettings, PeerNetworkSnapshot, Recommendation

try:
    from gui.jobs.ml_trainer import shadow_rebalance_predict as _shadow_rebalance_predict
except ImportError:  # scikit-learn not installed
    _shadow_rebalance_predict = None  # type: ignore[assignment]


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
    title: str,
    reasons: list[dict],
    data_window_days: int,
    confidence: float,
    confidence_label: str = Recommendation.CONFIDENCE_HEURISTIC,
    alternatives: list[str] | None = None,
    simulation_available: bool = True,
) -> dict:
    return {
        "title": title,
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


def _get_peer_network_context(pubkeys: list[str]) -> dict[str, dict]:
    """Return latest PeerNetworkSnapshot data keyed by pubkey (6-C).

    Used to enrich fee recommendations with gossip-network context:
    routing hubs (many channels, high capacity) justify competitive fees.
    Uses a Python-side dedup instead of DISTINCT ON to remain cross-database
    compatible (SQLite does not support DISTINCT ON).
    """
    if not pubkeys:
        return {}
    cutoff = timezone.now() - timedelta(hours=6)
    snapshots = (
        PeerNetworkSnapshot.objects
        .filter(pubkey__in=pubkeys, timestamp__gte=cutoff)
        .order_by("pubkey", "-timestamp")
    )
    result: dict[str, dict] = {}
    for s in snapshots:
        if s.pubkey not in result:
            result[s.pubkey] = {
                "alias": s.alias,
                "channel_count": s.channel_count,
                "total_capacity_sat": s.total_capacity_sat,
                "avg_fee_rate_ppm": round(s.avg_fee_rate_ppm, 1),
            }
    return result


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
    cutoff_30d = now - timedelta(days=30)
    cutoff_24h = now - timedelta(hours=24)
    drafts: list[RecommendationDraft] = []
    notify_cfg = NotificationSettings.load()
    mempool_payload = get_mempool_recommended_fees(enabled=notify_cfg.mempool_enabled)
    fee_signal = classify_fee_signal(mempool_payload)

    def _onchain_context() -> dict:
        if not mempool_payload or not fee_signal:
            return {}
        return {
            "source": "mempool.space",
            "fee_light": fee_signal.light,
            "fee_label": fee_signal.label,
            "wait_window": fee_signal.wait_window,
            "fastest_fee": mempool_payload.get("fastestFee"),
            "half_hour_fee": mempool_payload.get("halfHourFee"),
            "hour_fee": mempool_payload.get("hourFee"),
            "minimum_fee": mempool_payload.get("minimumFee"),
        }

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

    # 6-C: load gossip network context for peer dynamic adjustment
    channel_list = list(open_channels[:25])
    peer_pubkeys = list({ch.remote_pubkey for ch in channel_list if ch.remote_pubkey})
    peer_network_map = _get_peer_network_context(peer_pubkeys)

    for ch in channel_list:
        if len(drafts) >= limit:
            break
        capacity = ch.capacity or 1
        outbound_pct = int((ch.local_balance * 100) / capacity)
        inbound_pct = 100 - outbound_pct
        flow_30d = fwd_out_30d_map.get(ch.chan_id, {"total": 0, "volume": 0})
        peer_net = peer_network_map.get(ch.remote_pubkey, {})

        if ch.chan_id not in active_out_ids:
            # 6-C: routing hubs with many channels justify higher confidence on fee review
            hub_bonus = 0.04 if peer_net.get("channel_count", 0) >= 10 else 0.0
            confidence = min(0.92, 0.76 + hub_bonus)
            rationale = _build_rationale(
                title=f"Fee-Check: {ch.alias or ch.chan_id[:8]}",
                reasons=[
                    {"rank": 1, "signal": "no_outbound_flow", "value": "No outbound flow in 7 days", "weight": 0.5},
                    {"rank": 2, "signal": "stagnation_window", "value": "Review window: 14 days", "weight": 0.3},
                    {"rank": 3, "signal": "fee_position", "value": f"Current local fee rate: {ch.local_fee_rate} ppm", "weight": 0.2},
                ],
                data_window_days=14,
                confidence=confidence,
                alternatives=["rebalance", "close"],
            )
            if peer_net:
                rationale["network_context"] = peer_net
            drafts.append(
                RecommendationDraft(
                    rec_type=Recommendation.TYPE_FEE,
                    title=f"Fee-Check: {ch.alias or ch.chan_id[:8]}",
                    target_chan_id=ch.chan_id,
                    target_pubkey=ch.remote_pubkey,
                    risk_level=Recommendation.RISK_LOW,
                    confidence=confidence,
                    rationale=rationale,
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
                        title=f"Rebalance: {ch.alias or ch.chan_id[:8]}",
                        reasons=[
                            {"rank": 1, "signal": "balance_ratio", "value": f"{inbound_pct}% inbound", "weight": 0.5},
                            {"rank": 2, "signal": "outbound_capacity", "value": f"{outbound_pct}% outbound", "weight": 0.3},
                            {"rank": 3, "signal": "flow_history", "value": "Active forwarding observed", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["fee", "splice_in"],
                    ),
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
                        title=f"Splice In: {ch.alias or ch.chan_id[:8]}",
                        reasons=[
                            {"rank": 1, "signal": "high_outbound_flow", "value": f"{flow_30d.get('total', 0)} forwards in 30d", "weight": 0.45},
                            {"rank": 2, "signal": "low_outbound_liquidity", "value": f"{outbound_pct}% outbound remaining", "weight": 0.35},
                            {"rank": 3, "signal": "capacity_pressure", "value": "Channel likely constrained", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["open", "rebalance"],
                    ),
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
                        title=f"Splice Out: {ch.alias or ch.chan_id[:8]}",
                        reasons=[
                            {"rank": 1, "signal": "unused_capacity", "value": "Very low forwarding activity (30d)", "weight": 0.5},
                            {"rank": 2, "signal": "capacity_size", "value": f"Capacity: {capacity} sats", "weight": 0.3},
                            {"rank": 3, "signal": "efficiency", "value": "Consider reducing idle capital", "weight": 0.2},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["fee", "close"],
                    ),
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
                        title="Mitigate failed HTLC spike",
                        reasons=[
                            {"rank": 1, "signal": "failed_htlc_rate", "value": f"{failed_count} failed HTLCs in 24h", "weight": 0.6},
                            {"rank": 2, "signal": "routing_health", "value": "Potential route quality degradation", "weight": 0.25},
                            {"rank": 3, "signal": "stability", "value": "Investigate problematic peers/channels", "weight": 0.15},
                        ],
                        data_window_days=1,
                        confidence=confidence,
                        alternatives=["disable", "rebalance", "fee"],
                    ),
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
                        title="Diversify peer concentration",
                        reasons=[
                            {"rank": 1, "signal": "peer_concentration", "value": f"{concentration['channel_count']} channels to one peer", "weight": 0.6},
                            {"rank": 2, "signal": "resilience", "value": "Diversification reduces dependency risk", "weight": 0.25},
                            {"rank": 3, "signal": "routing_options", "value": "More peer diversity can increase route options", "weight": 0.15},
                        ],
                        data_window_days=30,
                        confidence=confidence,
                        alternatives=["rebalance"],
                    ),
                )
            )

    onchain_context = _onchain_context()
    created: list[Recommendation] = []
    for draft in sorted(drafts, key=lambda d: d.confidence, reverse=True)[:limit]:
        if draft.rec_type in {
            Recommendation.TYPE_OPEN,
            Recommendation.TYPE_CLOSE,
            Recommendation.TYPE_SPLICE_IN,
            Recommendation.TYPE_SPLICE_OUT,
        }:
            draft.rationale["onchain_fee_context"] = onchain_context
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


# ---------------------------------------------------------------------------
# Phase-6B: ML Shadow Recommendations
# ---------------------------------------------------------------------------

# Channels with outbound liquidity below this threshold (%) are considered depleted
_ML_SHADOW_DEPLETED_OUTBOUND_PCT = 30

def generate_ml_shadow_recommendations(*, limit: int = 3) -> list[dict]:
    """Generate ML shadow-mode recommendations alongside heuristic ones (R-AI-3).

    Rules:
    - Only runs when ai_mode in ('shadow', 'policy_bound')
    - Minimum data gate: ≥ 30 days + ≥ 50 events (R-AI-3)
    - Uses shadow_rebalance_predict from ml_trainer
    - Results are stored with confidence_label='ml_shadow'
    """
    from gui.models import RebalanceMLRecord, UserMode

    user_mode = UserMode.load()
    if user_mode.ai_mode not in (UserMode.AI_MODE_SHADOW, UserMode.AI_MODE_POLICY_BOUND):
        return []

    # Data gate check (R-AI-3)
    cutoff_30d = timezone.now() - timedelta(days=30)
    event_count = RebalanceMLRecord.objects.filter(timestamp__gte=cutoff_30d).count()
    if event_count < 50:
        return []  # Not enough data yet

    if _shadow_rebalance_predict is None:
        return []

    open_channels = list(
        Channels.objects.filter(
            is_open=True, is_active=True, ml_rebalance_enabled=True
        )[:limit * 2]
    )

    created: list[Recommendation] = []
    for ch in open_channels:
        if len(created) >= limit:
            break
        capacity = ch.capacity or 1
        outbound_pct = int((ch.local_balance * 100) / capacity)
        if outbound_pct > _ML_SHADOW_DEPLETED_OUTBOUND_PCT:
            continue  # Only suggest for depleted channels

        prediction = _shadow_rebalance_predict(
            source_chan_id="",
            target_chan_id=ch.chan_id,
            amount_sat=int(capacity * 0.2),
            fee_ppm=int(ch.local_fee_rate or 50),
        )
        prob = prediction.get("predicted_success_prob", 0.5)
        if prob < 0.55:
            continue  # Below confidence threshold

        model_version = prediction.get("model_version", "unknown")
        rationale = _build_rationale(
            title=f"ML Rebalance: {ch.alias or ch.chan_id[:8]}",
            reasons=[
                {"rank": 1, "signal": "ml_prediction", "value": f"ML success prob: {prob:.0%}", "weight": 0.6},
                {"rank": 2, "signal": "balance_ratio", "value": f"{outbound_pct}% outbound", "weight": 0.3},
                {"rank": 3, "signal": "model_version", "value": f"Model: {model_version}", "weight": 0.1},
            ],
            data_window_days=30,
            confidence=prob,
            confidence_label=Recommendation.CONFIDENCE_ML_SHADOW,
        )

        created.append(
            Recommendation.objects.create(
                rec_type=Recommendation.TYPE_REBALANCE,
                target_chan_id=ch.chan_id,
                target_pubkey=ch.remote_pubkey,
                rationale=rationale,
                confidence=prob,
                confidence_label=Recommendation.CONFIDENCE_ML_SHADOW,
                risk_level=Recommendation.RISK_LOW,
                status=Recommendation.STATUS_PENDING,
            )
        )
    return [_to_next_action(item) for item in created]
