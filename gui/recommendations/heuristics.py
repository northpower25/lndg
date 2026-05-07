def can_emit_ml_recommendation(data_days: int, relevant_events: int) -> bool:
    return data_days >= 30 and relevant_events >= 50
