"""Template context processors for LNDg."""


def user_mode(request):
    """Inject the current ``UserMode.mode`` into every template context."""
    from gui.models import UserMode

    try:
        mode = UserMode.load().mode
    except Exception:
        mode = UserMode.MODE_ADVANCED
    return {"user_mode": mode}
