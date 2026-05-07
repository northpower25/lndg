def normalize_snapshot_interval_minutes(
    configured_minutes: int | None, *, default_minutes: int = 15
) -> int:
    if configured_minutes is None:
        return default_minutes
    return configured_minutes if configured_minutes > 0 else default_minutes
