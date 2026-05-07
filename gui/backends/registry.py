"""Capability registry – a lightweight singleton for the active backend.

Usage::

    from gui.backends.registry import get_capabilities, set_active_backend

    # At startup / when the backend is configured:
    set_active_backend(lnd_backend_instance)

    # Anywhere in the read path (views, context processors, etc.):
    caps = get_capabilities()
    if caps.can_rebalance:
        ...

The active backend is stored at the module level.  ``set_active_backend`` must
be called before ``get_capabilities`` can return a real result; until then a
default ``BackendCapabilities`` (all flags False) is returned so that UI code
degrades gracefully.
"""

from __future__ import annotations

import logging

from .interfaces import BackendCapabilities, LightningReadAdapter

logger = logging.getLogger(__name__)

_active_backend: LightningReadAdapter | None = None


def set_active_backend(backend: LightningReadAdapter) -> None:
    """Register *backend* as the currently active backend adapter."""
    global _active_backend  # noqa: PLW0603
    _active_backend = backend
    logger.debug("Active backend set to %s", type(backend).__name__)


def get_active_backend() -> LightningReadAdapter | None:
    """Return the active backend adapter, or ``None`` if not set."""
    return _active_backend


def get_capabilities() -> BackendCapabilities:
    """Return the capabilities of the active backend.

    Returns a default ``BackendCapabilities`` (all flags False) when no
    backend has been registered yet, so callers always receive a valid object.
    """
    if _active_backend is None:
        return BackendCapabilities()
    try:
        return _active_backend.get_capabilities()
    except Exception:
        logger.exception("get_capabilities() failed – returning defaults")
        return BackendCapabilities()
