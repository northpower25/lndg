"""Template context processors for LNDg."""


def user_mode(request):
    """Inject the current ``UserMode.mode`` into every template context."""
    from gui.models import UserMode

    try:
        mode = UserMode.load().mode
    except Exception:
        mode = UserMode.MODE_ADVANCED
    return {"user_mode": mode}


def backend_capabilities(request):
    """Inject the active backend's ``BackendCapabilities`` into every template context.

    Templates can use ``{{ capabilities.can_rebalance }}`` etc. to conditionally
    enable or disable feature buttons (R-GUI-7, R-ARCH-2).
    """
    from gui.backends.registry import get_capabilities

    return {"capabilities": get_capabilities()}
