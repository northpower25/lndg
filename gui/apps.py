from django.apps import AppConfig


class GuiConfig(AppConfig):
    name = 'gui'

    def ready(self) -> None:
        """Register the active Lightning backend adapter in the capability registry.

        Called by Django once the application is fully loaded.  The method is
        intentionally lenient: any failure here must never prevent Django from starting.

        Backend selection logic:
        1. If LocalSettings contains ``CLN-REST-URL`` *and* ``CLN-Rune`` →
           :class:`gui.backends.cln_backend.ClnBackend`.
        2. Otherwise fall back to :class:`gui.backends.lnd_backend.LndBackend`.

        Database access is deferred to a ``request_started`` / ``post_migrate``
        signal to comply with Django's App-initialization guidelines (avoid DB
        queries in ``ready()``).  The default LndBackend (lazy connection) is
        registered synchronously so that ``get_capabilities()`` always returns a
        valid object from the first import.
        """
        import logging

        logger = logging.getLogger(__name__)

        # 1. Register the safe default (no DB access, lazy gRPC connection).
        try:
            from gui.backends.lnd_backend import LndBackend
            from gui.backends.registry import set_active_backend

            set_active_backend(LndBackend())
            logger.debug("BackendRegistry: default LndBackend registered.")
        except Exception:
            logger.exception("BackendRegistry: failed to register default LndBackend.")

        # 2. After migrations complete (or on the first request), re-check
        #    LocalSettings for CLN credentials and upgrade the backend if found.
        from django.core.signals import request_started
        from django.db.models.signals import post_migrate

        def _detect_cln_backend(sender=None, **kwargs):  # type: ignore[no-untyped-def]
            """Check LocalSettings for CLN credentials and update the registry."""
            try:
                from gui.backends.registry import get_active_backend, set_active_backend
                from gui.backends.cln_backend import ClnBackend
                from gui.models import LocalSettings

                cln_url_qs = LocalSettings.objects.filter(key="CLN-REST-URL")
                cln_rune_qs = LocalSettings.objects.filter(key="CLN-Rune")
                if cln_url_qs.exists() and cln_rune_qs.exists():
                    cln_url = cln_url_qs.first().value.strip()
                    cln_rune = cln_rune_qs.first().value.strip()
                    if cln_url and cln_rune:
                        # Only replace if not already a ClnBackend instance
                        current = get_active_backend()
                        if not isinstance(current, ClnBackend):
                            ca_cert_qs = LocalSettings.objects.filter(key="CLN-CA-Cert")
                            ca_cert = ca_cert_qs.first().value if ca_cert_qs.exists() else None
                            set_active_backend(
                                ClnBackend(base_url=cln_url, rune=cln_rune, ca_cert=ca_cert or None)
                            )
                            logger.info("BackendRegistry: upgraded to ClnBackend (%s).", cln_url)
            except Exception:
                logger.debug("BackendRegistry: CLN auto-detect skipped (DB not ready or other error).")
            finally:
                # Disconnect after first successful run to avoid repeated checks.
                request_started.disconnect(_detect_cln_backend)
                post_migrate.disconnect(_detect_cln_backend)

        request_started.connect(_detect_cln_backend)
        post_migrate.connect(_detect_cln_backend)

