"""Template context processors for LNDg."""


def user_mode(request):
    """Inject the current ``UserMode.mode`` into every template context."""
    from gui.models import UserMode

    try:
        user_mode = UserMode.load()
        mode = user_mode.mode
        language = user_mode.language or "en"
    except Exception:
        mode = UserMode.MODE_ADVANCED
        language = "en"
    return {"user_mode": mode, "user_language": language}


def backend_capabilities(request):
    """Inject the active backend's ``BackendCapabilities`` into every template context.

    Templates can use ``{{ capabilities.can_rebalance }}`` etc. to conditionally
    enable or disable feature buttons (R-GUI-7, R-ARCH-2).
    """
    from gui.backends.registry import get_capabilities

    return {"capabilities": get_capabilities()}
