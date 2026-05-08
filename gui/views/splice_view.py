from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from lndg import settings

from .utils import is_login_required


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/splice/'), settings.LOGIN_REQUIRED)
def splice_view(request):
    return render(
        request,
        "splice.html",
        {
            "page_mode": "advanced",
        },
    )


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/cln-plugins/'), settings.LOGIN_REQUIRED)
def cln_plugins_view(request):
    from gui.backends.registry import get_active_backend, get_capabilities

    capabilities = get_capabilities()
    backend = get_active_backend()
    plugins: list[dict] = []
    if capabilities.supports_plugins and backend is not None and hasattr(backend, "_post"):
        try:
            data = backend._post("listplugins")
            plugins = [
                {
                    "name": p.get("name", ""),
                    "active": bool(p.get("active", False)),
                    "dynamic": bool(p.get("dynamic", False)),
                    "version": p.get("version", ""),
                }
                for p in data.get("plugins", [])
            ]
        except Exception:
            plugins = []
    return render(
        request,
        "cln_plugins.html",
        {
            "plugins": plugins,
            "page_mode": "expert",
            "supports_plugins": capabilities.supports_plugins,
            "can_splice": capabilities.can_splice,
            "can_rebalance": capabilities.can_rebalance,
            "can_stream_htlcs": capabilities.can_stream_htlcs,
        },
    )
