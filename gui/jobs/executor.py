from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from gui.backends.interfaces import LightningWriteAdapter
from gui.backends.registry import get_active_backend
from gui.domain import FeePolicy, SpliceAction


def _get_write_backend() -> LightningWriteAdapter:
    backend = get_active_backend()
    if backend is None:
        raise RuntimeError("No active backend configured.")
    return backend


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_policy_snapshot(policy) -> dict[str, Any]:
    return {
        "policy_id": policy.id,
        "name": policy.name,
        "policy_type": policy.policy_type,
        "definition": policy.definition or {},
        "dry_run": policy.dry_run,
        "is_active": policy.is_active,
        "mode_required": policy.mode_required,
    }


def _execute_auto_fee_policy(policy, *, simulate: bool) -> dict[str, Any]:
    from gui.models import Channels, ChangeLog

    definition = policy.definition if isinstance(policy.definition, dict) else {}
    limits = definition.get("limits", {}) if isinstance(definition.get("limits"), dict) else {}
    target_channel_id = str(definition.get("channel_id", "")).strip()
    if not target_channel_id:
        return {
            "status": "blocked",
            "target_channel_id": "",
            "old_value": {},
            "new_value": {},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {"status": "blocked", "message": "Missing channel_id in policy definition."},
        }

    channel = Channels.objects.filter(chan_id=target_channel_id, is_open=True).first()
    if channel is None:
        return {
            "status": "blocked",
            "target_channel_id": target_channel_id,
            "old_value": {},
            "new_value": {},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {"status": "blocked", "message": "Channel not found or not open."},
        }

    backend = _get_write_backend()
    capabilities = backend.get_capabilities()
    if not capabilities.can_auto_fee:
        return {
            "status": "blocked",
            "target_channel_id": target_channel_id,
            "old_value": {"local_fee_rate": int(channel.local_fee_rate or 0)},
            "new_value": {},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {"status": "blocked", "message": "Backend does not support auto-fee updates."},
        }

    current_fee_rate = int(channel.local_fee_rate or 0)
    min_fee_rate = max(1, _as_int(definition.get("min_fee_rate_ppm"), default=1))
    max_fee_rate = max(min_fee_rate, _as_int(definition.get("max_fee_rate_ppm"), default=5000))
    max_delta_ppm = max(1, _as_int(limits.get("max_delta_ppm"), default=1000))
    max_delta_percent = max(1, _as_int(limits.get("max_delta_percent"), default=40))

    target_fee_rate = _as_int(definition.get("target_fee_rate_ppm"), default=current_fee_rate)
    if "delta_ppm" in definition:
        target_fee_rate = current_fee_rate + _as_int(definition.get("delta_ppm"), default=0)
    elif "delta_percent" in definition:
        target_fee_rate = int(current_fee_rate * (1 + (_as_int(definition.get("delta_percent"), default=0) / 100)))

    target_fee_rate = max(min_fee_rate, min(max_fee_rate, target_fee_rate))
    delta_ppm = target_fee_rate - current_fee_rate
    delta_percent = abs(delta_ppm) * 100 / max(1, current_fee_rate)
    if abs(delta_ppm) > max_delta_ppm or delta_percent > max_delta_percent:
        return {
            "status": "blocked",
            "target_channel_id": target_channel_id,
            "old_value": {"local_fee_rate": current_fee_rate},
            "new_value": {"local_fee_rate": target_fee_rate},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {"status": "blocked", "message": "Hard cap exceeded for fee delta."},
        }

    cooldown_minutes = max(1, _as_int(definition.get("cooldown_minutes"), default=60))
    cutoff = timezone.now() - timedelta(minutes=cooldown_minutes)
    if ChangeLog.objects.filter(
        change_type="policy_auto_fee",
        target_channel_id=target_channel_id,
        actor=f"policy:{policy.name}",
        timestamp__gte=cutoff,
    ).exists():
        return {
            "status": "cooldown",
            "target_channel_id": target_channel_id,
            "old_value": {"local_fee_rate": current_fee_rate},
            "new_value": {"local_fee_rate": target_fee_rate},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {"status": "cooldown", "message": "Cooldown guard active."},
        }

    old_value = {
        "local_fee_rate": current_fee_rate,
        "local_base_fee": int(channel.local_base_fee or 0),
        "local_inbound_fee_rate": int(channel.local_inbound_fee_rate or 0),
        "local_min_htlc_msat": int(channel.local_min_htlc_msat or 0),
        "local_max_htlc_msat": int(channel.local_max_htlc_msat or 0),
    }
    new_value = {
        "local_fee_rate": target_fee_rate,
        "local_base_fee": _as_int(definition.get("base_fee_msat"), default=old_value["local_base_fee"]),
        "local_inbound_fee_rate": _as_int(
            definition.get("inbound_fee_rate_ppm"),
            default=old_value["local_inbound_fee_rate"],
        ),
        "local_min_htlc_msat": _as_int(
            definition.get("min_htlc_msat"),
            default=old_value["local_min_htlc_msat"],
        ),
        "local_max_htlc_msat": _as_int(
            definition.get("max_htlc_msat"),
            default=old_value["local_max_htlc_msat"],
        ),
    }

    actions_taken = {
        "policy_type": policy.policy_type,
        "channel_id": target_channel_id,
        "executed": False,
    }
    if simulate:
        return {
            "status": "simulated",
            "target_channel_id": target_channel_id,
            "old_value": old_value,
            "new_value": new_value,
            "actions_taken": actions_taken,
            "outcome": {"status": "simulated", "message": "Dry-run completed."},
        }

    success = backend.update_fee_policy(
        channel_id=target_channel_id,
        policy=FeePolicy(
            channel_id=target_channel_id,
            fee_rate_ppm=new_value["local_fee_rate"],
            base_fee_msat=new_value["local_base_fee"],
            inbound_fee_rate_ppm=new_value["local_inbound_fee_rate"],
            min_htlc_msat=new_value["local_min_htlc_msat"],
            max_htlc_msat=new_value["local_max_htlc_msat"],
        ),
    )
    actions_taken["executed"] = bool(success)
    return {
        "status": "applied" if success else "failed",
        "target_channel_id": target_channel_id,
        "old_value": old_value,
        "new_value": new_value,
        "actions_taken": actions_taken,
        "outcome": {
            "status": "applied" if success else "failed",
            "message": "Auto-fee policy applied." if success else "Auto-fee update failed.",
        },
    }


def execute_policy(
    policy_id: int,
    *,
    simulate: bool = True,
    trigger_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from gui.models import ChangeLog, Policy, PolicyRun

    policy = Policy.objects.filter(pk=policy_id).first()
    if policy is None:
        return {"ok": False}

    snapshot = _build_policy_snapshot(policy)
    effective_simulate = bool(simulate) or bool(policy.dry_run)
    trigger_payload = dict(trigger_data or {})
    run = PolicyRun.objects.create(
        policy=policy,
        was_dry_run=effective_simulate,
        trigger_data={**trigger_payload, "policy_snapshot": snapshot},
        actions_taken={},
        outcome={},
    )

    if policy.policy_type == Policy.TYPE_AUTO_FEE:
        result = _execute_auto_fee_policy(policy, simulate=effective_simulate)
    elif policy.policy_type == Policy.TYPE_REBALANCE:
        result = {
            "status": "simulated" if effective_simulate else "scheduled",
            "target_channel_id": "",
            "old_value": {},
            "new_value": {},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {
                "status": "simulated" if effective_simulate else "scheduled",
                "message": "Rebalance policy recorded.",
            },
        }
    else:
        result = {
            "status": "simulated" if effective_simulate else "recorded",
            "target_channel_id": "",
            "old_value": {},
            "new_value": {},
            "actions_taken": {"policy_type": policy.policy_type, "executed": False},
            "outcome": {
                "status": "simulated" if effective_simulate else "recorded",
                "message": "Notify policy recorded.",
            },
        }

    run.actions_taken = result["actions_taken"]
    run.outcome = result["outcome"]
    run.save(update_fields=["actions_taken", "outcome"])
    policy.last_run = timezone.now()
    policy.save(update_fields=["last_run"])

    ChangeLog.objects.create(
        change_type=f"policy_{policy.policy_type}",
        target_channel_id=result.get("target_channel_id", ""),
        actor=f"policy:{policy.name}",
        old_value=result.get("old_value") or {"policy_snapshot": snapshot},
        new_value=result.get("new_value") or {"status": result["outcome"]["status"]},
        rationale={
            "policy_snapshot": snapshot,
            "trigger_data": trigger_payload,
            "risk_label": (policy.definition or {}).get("risk_label", "medium"),
            "outcome": result["outcome"],
        },
        policy_run_ref=str(run.id),
    )

    return {
        "ok": True,
        "status": result["status"],
        "policy_run_id": run.id,
        "was_dry_run": run.was_dry_run,
        "outcome": run.outcome,
        "actions_taken": run.actions_taken,
    }


def execute_due_policies(*, limit: int = 20) -> list[dict[str, Any]]:
    from gui.models import Policy

    now = timezone.now()
    due_policies = []
    for policy in Policy.objects.filter(is_active=True).order_by("id")[:limit]:
        definition = policy.definition if isinstance(policy.definition, dict) else {}
        interval_minutes = max(1, _as_int(definition.get("run_interval_minutes"), default=60))
        if policy.last_run and policy.last_run > now - timedelta(minutes=interval_minutes):
            continue
        due_policies.append(policy.id)

    results: list[dict[str, Any]] = []
    for policy_id in due_policies:
        results.append(
            execute_policy(
                policy_id=policy_id,
                simulate=False,
                trigger_data={"source": "scheduler"},
            )
        )
    return results


def execute_splice_in(channel_id: str, amount_sat: int, fee_rate: int) -> SpliceAction:
    backend = _get_write_backend()
    return backend.splice_in(channel_id=channel_id, amount_sat=amount_sat, fee_rate=fee_rate)


def execute_splice_out(
    channel_id: str, amount_sat: int, destination: str, fee_rate: int
) -> SpliceAction:
    backend = _get_write_backend()
    return backend.splice_out(
        channel_id=channel_id,
        amount_sat=amount_sat,
        destination=destination,
        fee_rate=fee_rate,
    )


def execute_splice_status(splice_id: str) -> SpliceAction:
    backend = _get_write_backend()
    return backend.get_splice_status(splice_id=splice_id)
