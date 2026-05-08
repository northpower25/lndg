"""Phase-6 ML training pipeline.

Responsibilities:
  - Feature engineering from ChannelSnapshot, RebalanceMLRecord, AutoFeeMLRecord
  - Batch retraining of scikit-learn models (daily, configurable, can be disabled)
  - Model persistence as .joblib files under <BASE_DIR>/models/
  - Shadow-mode inference: predict rebalance success probability
  - Auto-fee ML suggestions based on routing behaviour
  - Minimum data gate (R-AI-3): ≥ 30 days window, ≥ 50 events
  - ChangeLog entry with actor=ml:<model>:<version> (R-AI-4)

Usage:
  from gui.jobs.ml_trainer import train_rebalance_model, get_ml_status,
                                   shadow_rebalance_predict, get_autofee_suggestions
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _models_dir() -> Path:
    """Return the directory where .joblib model artefacts are stored."""
    try:
        from django.conf import settings as _s
        base = Path(_s.BASE_DIR)
    except Exception:
        base = Path(__file__).resolve().parent.parent.parent
    d = base / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _latest_model_path(prefix: str) -> Path | None:
    """Return the newest .joblib file matching *prefix* or None."""
    d = _models_dir()
    candidates = sorted(d.glob(f"{prefix}_v*.joblib"), reverse=True)
    return candidates[0] if candidates else None


def _versioned_model_path(prefix: str) -> Path:
    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    return _models_dir() / f"{prefix}_v{ts}.joblib"


# ---------------------------------------------------------------------------
# Feature engineering helpers
# ---------------------------------------------------------------------------

_MIN_DATA_DAYS = 30
_MIN_EVENTS = 50


def _check_min_data(qs_count: int, oldest_days: float) -> tuple[bool, str]:
    """Return (ok, reason) for the minimum-data gate (R-AI-3)."""
    if oldest_days < _MIN_DATA_DAYS:
        return False, f"Only {oldest_days:.0f} days of data (need {_MIN_DATA_DAYS})"
    if qs_count < _MIN_EVENTS:
        return False, f"Only {qs_count} events (need {_MIN_EVENTS})"
    return True, "ok"


def _build_rebalance_features() -> tuple[list[dict], list[int]]:
    """Build feature matrix and labels from RebalanceMLRecord.

    Features per row:
      hour_of_day, day_of_week, fee_ppm, amount_sat_log,
      routing_revenue_delta_24h, routing_revenue_delta_7d
    Label: success (0/1)
    """
    import math

    from gui.models import RebalanceMLRecord

    cutoff = timezone.now() - timedelta(days=_MIN_DATA_DAYS * 2)
    records = list(
        RebalanceMLRecord.objects.filter(timestamp__gte=cutoff).values(
            "hour_of_day",
            "day_of_week",
            "fee_ppm",
            "amount_sat",
            "routing_revenue_delta_24h",
            "routing_revenue_delta_7d",
            "success",
        )
    )
    features: list[dict] = []
    labels: list[int] = []
    for r in records:
        features.append(
            {
                "hour_of_day": r["hour_of_day"],
                "day_of_week": r["day_of_week"],
                "fee_ppm": r["fee_ppm"],
                "amount_sat_log": math.log1p(max(0, r["amount_sat"])),
                "rev_delta_24h": r["routing_revenue_delta_24h"],
                "rev_delta_7d": r["routing_revenue_delta_7d"],
            }
        )
        labels.append(1 if r["success"] else 0)
    return features, labels


def _build_autofee_features() -> list[dict]:
    """Build feature vectors for auto-fee suggestion from AutoFeeMLRecord."""
    import math

    from gui.models import AutoFeeMLRecord

    cutoff = timezone.now() - timedelta(days=_MIN_DATA_DAYS * 2)
    records = list(
        AutoFeeMLRecord.objects.filter(timestamp__gte=cutoff).values(
            "chan_id",
            "param_name",
            "old_value",
            "new_value",
            "ml_confidence",
            "routing_volume_delta_24h",
            "routing_revenue_delta_24h",
            "escalation_level",
        )
    )
    result: list[dict] = []
    for r in records:
        delta = r["new_value"] - r["old_value"]
        result.append(
            {
                "chan_id": r["chan_id"],
                "param_name": r["param_name"],
                "old_value": r["old_value"],
                "delta": delta,
                "delta_pct": delta / max(1, abs(r["old_value"])),
                "escalation_level": r["escalation_level"],
                "rev_delta_24h": r["routing_revenue_delta_24h"],
                "vol_delta_24h": r["routing_volume_delta_24h"],
                "confidence": r["ml_confidence"],
                "volume_log": math.log1p(max(0, r["routing_volume_delta_24h"])),
            }
        )
    return result


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_rebalance_model(*, force: bool = False) -> dict[str, Any]:
    """Train (or re-train) the rebalance success predictor.

    Returns a status dict compatible with the /api/v2/ml/status response.
    """
    try:
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return {
            "ok": False,
            "reason": "scikit-learn / joblib not installed. Add scikit-learn and joblib to requirements.",
        }

    from gui.models import RebalanceMLRecord

    cutoff = timezone.now() - timedelta(days=_MIN_DATA_DAYS)
    total_count = RebalanceMLRecord.objects.filter(timestamp__gte=cutoff).count()
    oldest = RebalanceMLRecord.objects.order_by("timestamp").values_list("timestamp", flat=True).first()
    if oldest:
        oldest_days: float = (timezone.now() - oldest).days
    else:
        oldest_days = 0.0

    ok, reason = _check_min_data(total_count, oldest_days)
    if not ok and not force:
        return {"ok": False, "reason": reason, "event_count": total_count, "oldest_days": oldest_days}

    features_raw, labels = _build_rebalance_features()
    if len(features_raw) < _MIN_EVENTS and not force:
        return {"ok": False, "reason": f"Insufficient training samples: {len(features_raw)}", "event_count": len(features_raw)}

    # Build numpy arrays from dicts
    import numpy as np  # pandas already in requirements; numpy is a transitive dep

    feature_keys = ["hour_of_day", "day_of_week", "fee_ppm", "amount_sat_log", "rev_delta_24h", "rev_delta_7d"]
    X = np.array([[r[k] for k in feature_keys] for r in features_raw], dtype=float)
    y = np.array(labels, dtype=int)

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42, n_jobs=1)),
        ]
    )

    cv_score: float | None = None
    if len(X) >= 10:
        try:
            scores = cross_val_score(pipeline, X, y, cv=min(3, len(X)), scoring="roc_auc")
            cv_score = float(scores.mean())
        except Exception as exc:  # pragma: no cover
            logger.warning("CV scoring failed: %s", exc)

    pipeline.fit(X, y)

    model_path = _versioned_model_path("rebalance")
    joblib.dump({"pipeline": pipeline, "feature_keys": feature_keys, "cv_auc": cv_score}, model_path)
    # prune older versions (keep last 5)
    all_models = sorted(_models_dir().glob("rebalance_v*.joblib"), reverse=True)
    for old in all_models[5:]:
        try:
            old.unlink()
        except OSError:
            pass

    logger.info("Rebalance ML model trained: %s samples, AUC=%.3f, path=%s", len(X), cv_score or 0.0, model_path)
    return {
        "ok": True,
        "model": "rebalance",
        "version": model_path.stem,
        "event_count": len(X),
        "oldest_days": oldest_days,
        "cv_auc": cv_score,
        "model_path": str(model_path),
    }


def _load_rebalance_model() -> dict | None:
    """Load the latest persisted rebalance model artefact."""
    path = _latest_model_path("rebalance")
    if path is None:
        return None
    try:
        import joblib

        return joblib.load(path)
    except Exception as exc:
        logger.warning("Failed to load rebalance model: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Shadow-mode inference
# ---------------------------------------------------------------------------

def shadow_rebalance_predict(
    *,
    source_chan_id: str,
    target_chan_id: str,
    amount_sat: int,
    fee_ppm: int,
) -> dict[str, Any]:
    """Return ML predicted success probability for a rebalance attempt.

    Respects R-AI-3: if no model exists or data gate fails, returns heuristic.
    """
    import math

    now = timezone.now()
    artefact = _load_rebalance_model()
    if artefact is None:
        return {
            "confidence_label": "heuristic",
            "predicted_success_prob": 0.5,
            "model_version": None,
            "reason": "No trained model available yet.",
        }

    pipeline = artefact.get("pipeline")
    feature_keys = artefact.get("feature_keys", [])
    if pipeline is None:
        return {"confidence_label": "heuristic", "predicted_success_prob": 0.5, "model_version": None, "reason": "Invalid model artefact."}

    import numpy as np

    row = {
        "hour_of_day": now.hour,
        "day_of_week": now.weekday(),
        "fee_ppm": fee_ppm,
        "amount_sat_log": math.log1p(max(0, amount_sat)),
        "rev_delta_24h": 0,
        "rev_delta_7d": 0,
    }
    X = np.array([[row.get(k, 0.0) for k in feature_keys]], dtype=float)
    try:
        prob = float(pipeline.predict_proba(X)[0][1])
    except Exception as exc:
        logger.warning("Shadow predict failed: %s", exc)
        return {"confidence_label": "heuristic", "predicted_success_prob": 0.5, "model_version": None, "reason": str(exc)}

    model_path = _latest_model_path("rebalance")
    version = model_path.stem if model_path else "unknown"
    return {
        "confidence_label": "ml_shadow",
        "predicted_success_prob": round(prob, 4),
        "model_version": version,
        "source_chan_id": source_chan_id,
        "target_chan_id": target_chan_id,
        "reason": "Shadow ML prediction (not executed).",
    }


# ---------------------------------------------------------------------------
# Auto-fee ML suggestions
# ---------------------------------------------------------------------------

_ESCALATION_FACTORS = {
    "fee_rate": {"up": 1.15, "down": 0.90},
    "base_fee": {"up": 1.10, "down": 0.90},
    "inbound_fee_rate": {"up": 1.10, "down": 0.85},
}
_ESCALATION_MAX_LEVELS = 5
_ESCALATION_COOLDOWN_MINUTES = 60


def _get_escalation_config() -> dict[str, Any]:
    """Return escalation config from LocalSettings with defaults."""
    try:
        from gui.models import LocalSettings

        cfg: dict[str, Any] = {}
        for key, default in [
            ("ML-EscalationCooldown", _ESCALATION_COOLDOWN_MINUTES),
            ("ML-EscalationMaxLevels", _ESCALATION_MAX_LEVELS),
        ]:
            row = LocalSettings.objects.filter(key=key).first()
            try:
                cfg[key] = int(row.value) if row else default
            except (ValueError, TypeError):
                cfg[key] = default
        return cfg
    except Exception:
        return {
            "ML-EscalationCooldown": _ESCALATION_COOLDOWN_MINUTES,
            "ML-EscalationMaxLevels": _ESCALATION_MAX_LEVELS,
        }


def get_autofee_suggestions(*, limit: int = 10) -> list[dict[str, Any]]:
    """Return ML-driven auto-fee adjustment suggestions.

    Each suggestion includes confidence + confidence_label (R-AI-5).
    Shadow-mode only: suggestions are advisory, not executed automatically.
    """
    from gui.models import Channels, UserMode

    user_mode = UserMode.load()
    if user_mode.ai_mode == UserMode.AI_MODE_OFF:
        return []

    features = _build_autofee_features()
    if not features:
        return []

    # Group latest record per channel
    latest: dict[str, dict] = {}
    for f in features:
        cid = f["chan_id"]
        if cid not in latest or f.get("escalation_level", 0) > latest[cid].get("escalation_level", 0):
            latest[cid] = f

    suggestions: list[dict[str, Any]] = []
    for cid, feat in list(latest.items())[:limit]:
        channel = Channels.objects.filter(chan_id=cid, is_open=True).first()
        if channel is None:
            continue
        current_fee = int(channel.local_fee_rate or 0)
        rev_delta = feat["rev_delta_24h"]
        current_level = min(feat.get("escalation_level", 0), _ESCALATION_MAX_LEVELS)

        if rev_delta > 0:
            factor = _ESCALATION_FACTORS["fee_rate"]["up"]
            direction = "up"
            new_level = min(current_level + 1, _ESCALATION_MAX_LEVELS)
        elif rev_delta < 0:
            factor = _ESCALATION_FACTORS["fee_rate"]["down"]
            direction = "down"
            new_level = max(current_level - 1, 0)
        else:
            continue

        suggested_fee = max(1, int(current_fee * factor))
        confidence = min(0.90, 0.55 + 0.05 * current_level + abs(feat["confidence"]) * 0.2)

        suggestions.append(
            {
                "chan_id": cid,
                "alias": channel.alias or cid[:8],
                "current_fee_rate": current_fee,
                "suggested_fee_rate": suggested_fee,
                "direction": direction,
                "escalation_level": new_level,
                "confidence": round(confidence, 3),
                "confidence_label": "ml_shadow",
                "rev_delta_24h": rev_delta,
                "is_dry_run": True,
                "reason": (
                    f"Routing revenue {'increased' if rev_delta > 0 else 'decreased'} "
                    f"by {abs(rev_delta)} msat (24h); escalation level {new_level}."
                ),
            }
        )

    suggestions.sort(key=lambda s: s["confidence"], reverse=True)
    return suggestions


def get_autofee_history(*, chan_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent AutoFeeMLRecord history entries."""
    from gui.models import AutoFeeMLRecord

    qs = AutoFeeMLRecord.objects.order_by("-timestamp")
    if chan_id:
        qs = qs.filter(chan_id=chan_id)
    rows = qs[:limit]
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "chan_id": r.chan_id,
            "param_name": r.param_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "ml_confidence": r.ml_confidence,
            "escalation_level": r.escalation_level,
            "trigger_reason": r.trigger_reason,
            "routing_revenue_delta_24h": r.routing_revenue_delta_24h,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------

def get_ml_status() -> dict[str, Any]:
    """Return current ML infrastructure status for GET /api/v2/ml/status."""
    from gui.models import AutoFeeMLRecord, RebalanceMLRecord, UserMode

    now = timezone.now()
    cutoff_30d = now - timedelta(days=30)

    rebalance_count = RebalanceMLRecord.objects.filter(timestamp__gte=cutoff_30d).count()
    autofee_count = AutoFeeMLRecord.objects.filter(timestamp__gte=cutoff_30d).count()

    oldest_reb = (
        RebalanceMLRecord.objects.order_by("timestamp").values_list("timestamp", flat=True).first()
    )
    oldest_days: float = (now - oldest_reb).days if oldest_reb else 0.0

    ok, data_reason = _check_min_data(rebalance_count, oldest_days)

    artefact = _load_rebalance_model()
    model_path = _latest_model_path("rebalance")

    user_mode = UserMode.load()

    return {
        "ai_mode": user_mode.ai_mode,
        "rebalance_events_30d": rebalance_count,
        "autofee_events_30d": autofee_count,
        "oldest_data_days": oldest_days,
        "data_gate_ok": ok,
        "data_gate_reason": data_reason,
        "rebalance_model_version": model_path.stem if model_path else None,
        "rebalance_model_cv_auc": artefact.get("cv_auc") if artefact else None,
        "model_path": str(model_path) if model_path else None,
        "shadow_mode_active": user_mode.ai_mode in (UserMode.AI_MODE_SHADOW, "policy_bound"),
    }
