"""ML Settings view – dedicated control page for ML feature configuration.

Provides:
  - Global ML mode + AI feature flags (persisted in UserMode)
  - Escalation/training config (persisted in LocalSettings)
  - Per-channel ML toggles (ml_rebalance_enabled / ml_autofee_enabled)
  - Live ML status summary (model availability, data gate)
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from lndg import settings

from .utils import is_login_required


@is_login_required(
    login_required(login_url='/lndg-admin/login/?next=/ml-settings/'),
    settings.LOGIN_REQUIRED,
)
def ml_settings_view(request):
    """Render the ML Control page (advanced / expert mode)."""
    from gui.models import Channels, LocalSettings, UserMode

    user_mode_obj = UserMode.load()

    # ── ML status (skip on ImportError – no ML flavor image) ─────────────────
    ml_status: dict = {}
    try:
        from gui.jobs.ml_trainer import get_ml_status
        ml_status = get_ml_status()
    except ImportError:
        ml_status = {"ml_available": False, "reason": "ML packages not installed."}
    except Exception as exc:
        ml_status = {"ml_available": False, "reason": str(exc)}

    # ── Escalation / training config from LocalSettings ───────────────────────
    _esc_defaults: list[tuple[str, str]] = [
        ("ML-TrainingEnabled", "true"),
        ("ML-TrainingIntervalHours", "24"),
        ("ML-EscalationCooldown", "60"),
        ("ML-EscalationMaxLevels", "5"),
        ("ML-EscalationFeeRateUp", "1.15"),
        ("ML-EscalationFeeRateDown", "0.90"),
    ]
    escalation_config: dict[str, str] = {}
    for key, default in _esc_defaults:
        row = LocalSettings.objects.filter(key=key).first()
        escalation_config[key] = row.value if row else default

    # ── Per-channel table ─────────────────────────────────────────────────────
    open_channels = (
        Channels.objects.filter(is_open=True)
        .order_by("alias", "chan_id")
        .values(
            "chan_id",
            "alias",
            "local_balance",
            "remote_balance",
            "capacity",
            "ml_rebalance_enabled",
            "ml_autofee_enabled",
        )
    )

    context = {
        "user_mode": user_mode_obj.mode,
        "ai_mode": user_mode_obj.ai_mode,
        "ai_policy_bound_confirm": user_mode_obj.ai_policy_bound_confirm,
        "ai_shadow_log_enabled": user_mode_obj.ai_shadow_log_enabled,
        "ai_min_data_days": user_mode_obj.ai_min_data_days,
        "ai_max_auto_actions_day": user_mode_obj.ai_max_auto_actions_day,
        "ai_cooldown_minutes": user_mode_obj.ai_cooldown_minutes,
        "ai_mode_choices": [
            ("off", "Off – no ML features active"),
            ("advisory", "Advisory – show suggestions, no execution"),
            ("shadow", "Shadow – log predictions, no execution"),
            ("policy_bound", "Policy-Bound (Expert) – execute with confirmation"),
        ],
        "escalation_config": escalation_config,
        "ml_status": ml_status,
        "channels": list(open_channels),
    }
    return render(request, "ml_settings.html", context)
