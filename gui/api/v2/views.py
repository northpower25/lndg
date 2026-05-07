from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle


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
